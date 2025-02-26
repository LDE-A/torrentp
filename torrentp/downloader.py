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
                    'choking_algorithm': 1,          # 最適なアンチョークアルゴリズム
                    'seed_choking_algorithm': 1,     # 最適なシードチョークアルゴリズム
                    'use_parole_mode': True,         # 仮釈放モード（効率的ピア管理）
                    'smooth_connects': True,         # 接続平滑化
                    'dont_count_slow_torrents': True, # 低速トレントを制限に含めない
                    'auto_scrape_interval': 1800,    # スクレイプ間隔（秒）
                    'close_redundant_connections': True, # 冗長接続を閉じる
                    'prioritize_partial_pieces': True, # 部分ピースの優先
                    'rate_limit_ip_overhead': False, # オーバーヘッドを制限しない
                    'max_failcount': 3,             # 再試行回数
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
        self._end_game_threshold: float = 0.95  # 95%でEnd Gameモード開始

    def status(self):
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
        else:
            self._add_torrent_params = self._torrent_info
            self._add_torrent_params.save_path = self._save_path
            self._file = self._session.add_torrent(self._add_torrent_params)
            self._status = self._file.status()
            while(not self._file.has_metadata()):
                time.sleep(1)

        # ファイル追加後に追加設定
        if self._file:
            # わたくしお気に入りの洗練されたピース選択戦略ですわ
            self._file.set_sequential_download(False)  # ランダムダウンロードの方が高速ですの

            # 初回起動ブーストを適用（最初の数ピースを優先）
            if not hasattr(self, '_initial_boost_applied') or not self._initial_boost_applied:
                try:
                    info = self._file.get_torrent_info()
                    piece_count = info.num_pieces()
                    if piece_count > 10:
                        # 最初と最後のピースを優先して良いスタートと早い再生準備を！
                        priorities = [7] * 5  # 最初の5ピースを最高優先
                        priorities.extend([1] * (piece_count - 10))  # 中間は通常優先
                        priorities.extend([7] * 5)  # 最後の5ピースを最高優先
                        self._file.prioritize_pieces(priorities)
                    self._initial_boost_applied = True
                except Exception:
                    pass

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

            # わたくしからの贈り物、高貴なETAトラッキング用の変数ですわ
            progress_samples: list = []
            last_bytes_downloaded: int = 0

            while not self._status.is_seeding:
                if not self._paused:
                    status = self.status()

                    # End Gameモードの制御（ダウンロード終盤での最適化）
                    if not self._end_game_mode and status.progress > self._end_game_threshold:
                        self._end_game_mode = True
                        # End Gameモードでは全ての残りピースをすべてのピアに要求！
                        self._file.set_download_mode(self._lt.download_mode.download_metadata)
                        self._file.set_download_mode(self._lt.download_mode.download_content)

                    # ETAの計算（平民にはありがたいですわね）
                    bytes_downloaded = status.total_wanted_done
                    progress_change = bytes_downloaded - last_bytes_downloaded
                    if progress_change > 0:
                        self._download_started = True
                        progress_samples.append((time.time(), bytes_downloaded))
                        # 古いサンプルを削除（直近30秒のみ使用）
                        current_time = time.time()
                        progress_samples = [s for s in progress_samples if current_time - s[0] < 30]
                    last_bytes_downloaded = bytes_downloaded

                    # 進捗状況表示を更新（ETAを含む）
                    self._get_status_progress(status, progress_samples)
                    self._check_timeout(status.progress)
                    sys.stdout.flush()

                await asyncio.sleep(1)

            if self._stop_after_download:
                self.stop()
            else:
                print('\033[92m' + "\nダウンロードが完了いたしましたわ。" + '\033[0m')

                # わたくしの考案した高貴なシードブースト機能ですわ！
                if not hasattr(self, '_seed_time') or not self._seed_time:
                    self._seed_time = 300  # 5分間シード

                print(f'\033[95m貴方のためにシードを{self._seed_time}秒間行って差し上げますわ\033[0m')
                seed_start = time.time()
                while time.time() - seed_start < self._seed_time and not self._paused:
                    status = self.status()
                    upload_speed = status.upload_rate / 1000
                    elapsed = time.time() - seed_start
                    remaining = max(0, self._seed_time - elapsed)

                    # 高貴なシード状況表示
                    print(f"\rシード中: {upload_speed:.1f} KB/s | 残り: {int(remaining)}秒", end='')
                    await asyncio.sleep(1)

                print("\nシードが完了いたしましたわ。")
                self.stop()

        except DownloadTimeoutError as e:
            self.stop()
            raise e
        except Exception as e:
            self._cleanup_files()
            self.stop()
            raise Exception(f"\nダウンロード中に予期せぬ問題が発生いたしましたわ: {e}")

    def _get_status_progress(self, s, progress_samples=None):
        _percentage = s.progress * 100
        _download_speed = s.download_rate / 1000 / 1000
        _upload_speed = s.upload_rate / 1000

        counting = math.ceil(_percentage / 5)
        visual_loading = '#' * counting + ' ' * (20 - counting)

        # ETAの計算
        eta_message = ''
        if progress_samples and len(progress_samples) > 1:
            elapsed_time = progress_samples[-1][0] - progress_samples[0][0]
            bytes_downloaded = progress_samples[-1][1] - progress_samples[0][1]
            if bytes_downloaded > 0:
                download_rate = bytes_downloaded / elapsed_time
                bytes_remaining = s.total_wanted - s.total_wanted_done
                eta = bytes_remaining / download_rate
                eta_message = f" | ETA: {int(eta)}秒"

        _message = "\r\033[42m %.2f mb/s \033[0m|\033[46m up: %.1f Kb/s \033[0m| status: %s | peers: %d  \033[96m|%s|\033[0m %d%%%s" % (_download_speed, _upload_speed, s.state, s.num_peers, visual_loading, _percentage, eta_message)
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
