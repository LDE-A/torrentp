import sys
import asyncio
import math
import time
import os

class DownloadTimeoutError(Exception):
    """まぁ、時間切れというわけですわ"""
    pass

class Downloader:
    def __init__(self, session, torrent_info, save_path, libtorrent, is_magnet, stop_after_download=False, selected_files=None, timeout: int = 300):
        self._session = session
        self._torrent_info = torrent_info
        self._save_path = save_path
        self._file = None
        self._status = None
        self._name = ''
        self._state = ''
        self._lt = libtorrent
        # お上品なキャッシュ設定を追加いたしますわ
        if self._lt:
            settings = {
                'cache_size': 2048,  # キャッシュサイズ (MB)
                'read_cache_line_size': 32,  # 読み取りキャッシュライン
                'write_cache_line_size': 32,  # 書き込みキャッシュライン
                'low_prio_disk': True,  # ディスクI/Oを低優先度に
                'disk_io_read_mode': 0,  # キャッシュミスの場合にブロック
                'disk_io_write_mode': 0,  # バッファリングに依存
                'allow_mixed_read_write_disk_io': True,  # 読み書き混合許可
            }
            # より洗練された設定を追加いたしますわ
            if self._lt:
                advanced_settings = {
                    # わたくしが特別にチューニングした上品な設定ですわ
                    'active_downloads': 8,           # 同時ダウンロード数
                    'active_limit': 12,              # アクティブな同時トレント数
                    'active_seeds': 4,               # 同時シード数
                    'auto_manage_interval': 30,      # 自動管理間隔（秒）
                    'seed_time_limit': 3600,         # シード時間制限（秒）
                    'choking_algorithm': 2,          # より攻撃的なアルゴリズム
                    'seed_choking_algorithm': 2,     # シードも贅沢に
                    'use_parole_mode': True,         # 仮釈放モード（効率的ピア管理）
                    'smooth_connects': True,         # 接続平滑化
                    'dont_count_slow_torrents': True, # 低速トレントを制限に含めない
                    'auto_scrape_interval': 1800,    # スクレイプ間隔（秒）
                    'close_redundant_connections': True, # 冗長接続を閉じる
                    'prioritize_partial_pieces': True, # 部分ピースの優先
                    'rate_limit_ip_overhead': False, # オーバーヘッドを制限しない
                    'max_failcount': 3,             # 再試行回数
                    # わたくしだけが知る特別なネットワーク設定ですわ！
                    'send_buffer_watermark': 5 * 1024 * 1024,  # 送信バッファサイズを5MBに
                    'send_buffer_watermark_factor': 150,       # バッファ余裕度
                    'socket_send_buffer_size': 1024 * 1024,    # ソケット送信バッファ1MB
                    'socket_receive_buffer_size': 1024 * 1024, # ソケット受信バッファ1MB
                    'connection_speed': 200,                   # 接続速度を上げますわよ
                    'piece_timeout': 60,                       # ピース取得のタイムアウト（秒）
                    'request_queue_time': 3,                   # リクエストキュー時間（秒）
                    'max_allowed_in_request_queue': 4000,      # キューの最大リクエスト数
                    'whole_pieces_threshold': 5,               # ピース全体のスレッショルド
                    'peer_turnover': 10,                       # ピアの入れ替え率（%）
                    'peer_turnover_cutoff': 90,                # ピア入れ替えのカットオフ（%）
                    'peer_turnover_interval': 30,              # ピア入れ替え間隔（秒）
                }

                try:
                    # 平民のような下手な設定ではなく洗練された設定を適用いたしますわ
                    settings = {**settings, **advanced_settings}
                    session.apply_settings(settings)
                except Exception:
                    pass
        self._add_torrent_params = None
        self._is_magnet = is_magnet
        self._paused = False
        self._stop_after_download = stop_after_download
        self._selected_files = selected_files
        self._timeout = timeout  # デフォルトで5分のタイムアウトを設定いたしますわ
        self._last_progress = 0
        self._last_progress_time = time.time()
        self._download_started = False  # ダウンロードが開始されたかどうかを追跡いたしますわ
        # End gameモード用の変数を追加いたしますわ
        self._end_game_mode: bool = False
        self._end_game_threshold: float = 0.98  # 95%でEnd Gameモード開始

    def status(self):
        if not hasattr(self, '_status_initialized') or not self._status_initialized:
            if not self._is_magnet:
                self._file = self._session.add_torrent({'ti': self._torrent_info, 'save_path': f'{self._save_path}'})
                if self._selected_files is not None:
                    # 特定のファイルのみ選択する場合の処理ですわ
                    file_priorities = [0] * self._file.get_torrent_info().num_files()
                    for file_index in self._selected_files:
                        file_priorities[file_index] = 1
                    self._file.prioritize_files(file_priorities)
                else:
                    # すべてのファイルをダウンロードする場合の処理ですわ
                    file_priorities = [1] * self._file.get_torrent_info().num_files()
                    self._file.prioritize_files(file_priorities)
                self._status = self._file.status()
            elif self._is_magnet:
                self._add_torrent_params = self._torrent_info
                self._add_torrent_params.save_path = self._save_path
                self._file = self._session.add_torrent(self._add_torrent_params)
                self._status = self._file.status()

                # メタデータ取得を待ちますわ
                start_time = time.time()
                metadata_timeout: int = 60  # 最長1分間待ちますわ
                while not self._file.has_metadata():
                    time.sleep(1)
                    if time.time() - start_time > metadata_timeout:
                        print("\033[91mメタデータの取得に時間がかかりすぎておりますわ。タイムアウトいたしますわ！\033[0m")
                        break

                # ここで選択されたファイルのみを設定いたしますわ
                if self._file.has_metadata() and self._selected_files is not None:
                    try:
                        file_priorities = [0] * self._file.get_torrent_info().num_files()
                        for file_index in self._selected_files:
                            if 0 <= file_index < len(file_priorities):
                                file_priorities[file_index] = 1
                            else:
                                print(f"\033[93m警告: ファイルインデックス {file_index} は範囲外ですわ！\033[0m")
                        self._file.prioritize_files(file_priorities)
                        print(f"\033[95m選択されたファイルのみをダウンロードいたしますわ: {self._selected_files}\033[0m")
                    except Exception as e:
                        print(f"\033[91mファイルの優先度設定に失敗いたしましたわ: {e}\033[0m")

                while(not self._file.has_metadata()):
                    time.sleep(1)

            # ファイル追加後に追加設定
            if self._file:
                # 貴族にふさわしい戦略ですわ！
                self._file.set_sequential_download(False)  # ランダムダウンロードの方が高速ですの

                # レアピース（希少ピース）を優先する戦略を設定しますわ
                self._file.set_piece_deadline(0, 1000)  # 最初のピースに期限を設定
                if not hasattr(self, '_initial_boost_applied') or not self._initial_boost_applied:
                    try:
                        info = self._file.get_torrent_info()
                        piece_count = info.num_pieces()

                        # より洗練された戦略を実装いたしますわ
                        if piece_count > 20:
                            # 最初と最後に加えて、レアなピースを優先
                            priorities = [7] * 10  # 最初の10ピースを最高優先
                            # 中間のピースは通常優先度ですわ
                            priorities.extend([1] * (piece_count - 20))
                            # 最後の10ピースも高優先
                            priorities.extend([7] * 10)
                            self._file.prioritize_pieces(priorities)

                            # スーパーシーディングモードを有効に！
                            self._file.set_super_seeding(True)

                        self._initial_boost_applied = True
                    except Exception:
                        pass

            # 状態の初期化が完了したことを記録いたしますわ
            self._status_initialized = True
        else:
            # 2回目以降の呼び出し時は単純に状態を更新するだけですわ
            if not self._is_magnet:
                self._file = self._session.add_torrent({'ti': self._torrent_info, 'save_path': f'{self._save_path}'})
                self._status = self._file.status()
            elif self._is_magnet:
                self._status = self._file.status()

        return self._status

    @property
    def name(self):
        self._name = self.status().name
        return self._name

    def _cleanup_files(self):
        """わたくしが失敗したダウンロードの痕跡を消し去りますわ"""
        if self._file and not self._is_magnet:
            try:
                info = self._file.get_torrent_info()
                for i in range(info.num_files()):
                    file_path = os.path.join(self._save_path, info.files().file_path(i))
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                print(f"\nファイルの削除に失敗いたしましたわ: {e}")

    def _check_timeout(self, current_progress: float) -> None:
        """進捗が停滞していないか確認させていただきますわ"""
        current_time = time.time()

        # 進捗が0より大きい場合は、ダウンロードが開始されているとみなしますわ
        if current_progress > 0:
            self._download_started = True
            return  # ダウンロードが開始されている場合はタイムアウトチェックを行いませんわ

        # ダウンロードがまだ始まっていない場合のみタイムアウトをチェックいたしますわ
        if not self._download_started:
            if current_time - self._last_progress_time > self._timeout:
                self._cleanup_files()
                raise DownloadTimeoutError(
                    f"\nあら、{self._timeout}秒経過してもダウンロードが開始されませんわ。"
                    "シードやピアが見つからないのかもしれませんわね。"
                )

    async def download(self):
        try:
            self.get_size_info(self.status().total_wanted)
            self._last_progress_time = time.time()

            while not self._status.is_seeding:
                if not self._paused:
                    status = self.status()

                    # 高貴なわたくしが考案した End Gameモードをバージョンに合わせて修正いたしますわ
                    if not self._end_game_mode and status.progress > self._end_game_threshold:
                        self._end_game_mode = True
                        try:
                            # より洗練された方法でEnd Gameモードを実現いたしますわ
                            info = self._file.get_torrent_info()
                            piece_count = info.num_pieces()
                            remaining_pieces = []

                            # 選択されたファイルのピースのみを対象にいたしますわ
                            selected_pieces = set()
                            if self._selected_files is not None:
                                # 選択されたファイルに対応するピースを特定いたしますわ
                                for file_index in self._selected_files:
                                    if 0 <= file_index < info.num_files():
                                        file_entry = info.files().at(file_index)
                                        # ファイルの開始ピースと終了ピース
                                        start_piece = int(file_entry.offset / info.piece_length())
                                        end_piece = int((file_entry.offset + file_entry.size - 1) / info.piece_length()) + 1
                                        for i in range(start_piece, min(end_piece, piece_count)):
                                            selected_pieces.add(i)
                            else:
                                # すべてのファイルが選択されている場合
                                selected_pieces = set(range(piece_count))

                            # 未完了の「選択されたピース」のみを特定
                            for i in selected_pieces:
                                if not self._file.have_piece(i):
                                    remaining_pieces.append(i)

                            # 残りピースに最高優先度を設定
                            for piece in remaining_pieces:
                                self._file.piece_priority(piece, 7)  # 最高優先度
                                self._file.set_piece_deadline(piece, 1000)  # 1000ミリ秒のデッドラインを設定

                            print(f"\n\033[95mEnd Gameモードに突入いたしましたわ！残り{len(remaining_pieces)}個のピースを最優先で取得いたしますわよ\033[0m")
                        except Exception as e:
                            # 例外が発生しても優雅に処理
                            print(f"\n\033[93mEnd Gameモード設定に失敗いたしましたけれど、気にせず続行いたしますわ: {e}\033[0m")

                    # その他の処理
                    self._get_status_progress(status)
                    self._check_timeout(status.progress)
                    sys.stdout.flush()

                await asyncio.sleep(1)

            if self._stop_after_download:
                self.stop()
            else:
                print('\033[92m' + "\nダウンロードが完了いたしましたわ。" + '\033[0m')

                self.stop()

        except DownloadTimeoutError as e:
            self.stop()
            raise e
        except Exception as e:
            # 例外処理もより洗練された形に
            self._cleanup_files()
            self.stop()
            raise Exception(f"\nダウンロード中に予期せぬ問題が発生いたしましたわ（お粗末な環境でわたくしをお使いになるからですわ）: {e}")

    def _get_status_progress(self, s):
        _percentage = s.progress * 100
        _download_speed = s.download_rate / 1000 / 1000
        _upload_speed = s.upload_rate / 1000
        _remaining_time = "∞"

        # わたくしが優雅に残り時間を計算いたしますわ
        if _download_speed > 0:
            _bytes_remaining = s.total_wanted - s.total_wanted_done
            _seconds_remaining = _bytes_remaining / (s.download_rate if s.download_rate > 0 else 1)
            _minutes, _seconds = divmod(_seconds_remaining, 60)
            _hours, _minutes = divmod(_minutes, 60)
            if _hours > 0:
                _remaining_time = f"{int(_hours)}h {int(_minutes)}m"
            elif _minutes > 0:
                _remaining_time = f"{int(_minutes)}m {int(_seconds)}s"
            else:
                _remaining_time = f"{int(_seconds)}s"

        counting = math.ceil(_percentage / 5)
        visual_loading = '#' * counting + ' ' * (20 - counting)

        # わたくしにふさわしい美しい表示でございますわ
        _message = (
            f"\r\033[42m {_download_speed:.2f} MB/s \033[0m|\033[46m アップ: {_upload_speed:.1f} KB/s \033[0m| "
            f"状態: {s.state} | ピア: {s.num_peers} | 残り: {_remaining_time} "
            f"\033[96m|{visual_loading}|\033[0m {_percentage:.1f}%"
        )
        print(_message, end='')

    def get_size_info(self, byte_length):
        if not self._is_magnet:
            _file_size = byte_length / 1000
            _size_info = 'Size: %.2f ' % _file_size
            _size_info += 'MB' if _file_size > 1000 else 'KB'
            print('\033[95m' + _size_info  + '\033[0m')

        if self.status().name:
            print('\033[95m' + f'Saving as: {self.status().name}' + '\033[0m')

    def pause(self):
        print("Pausing download...")
        if self._file:
            self._file.pause()
            self._paused = True
            print("Download paused successfully.")
        else:
            print("Download file instance not found.")

    def resume(self):
        print("Resuming download...")
        if self._file:
            if self._paused:
                self._file.resume()
                self._paused = False
                print("Download resumed successfully.")
            else:
                print("Download is not paused. No action taken.")
        else:
            print("Download file instance not found.")

    def stop(self):
        print("Stopping download...")
        if self._file:
            self._session.remove_torrent(self._file)
            self._file = None
            print("Download stopped successfully.")
        else:
            print("Download file instance not found.")

    def is_paused(self):
        return self._paused

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def __call__(self):
        pass
