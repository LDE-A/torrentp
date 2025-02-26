from .session import Session
from .torrent_info import TorrentInfo
from .downloader import Downloader
import libtorrent as lt
import time


class TorrentDownloader:
    def __init__(self, file_path: str, save_path: str, port: int = 6881,
                 stop_after_download: bool = False, selected_files: list = None,
                 timeout: int = 300):
        self._file_path = file_path
        self._save_path = save_path
        self._port = port  # Default port is 6881
        self._downloader = None
        self._torrent_info = None
        self._lt = lt
        self._file = None
        self._add_torrent_params = None
        self._session = Session(self._lt, port=self._port)  # Pass port to Session
        self._stop_after_download = stop_after_download
        self._selected_files = selected_files
        self._timeout = timeout

    def get_files_info(self):
        """わたくしがトレントファイルの内容を表示させていただきますわ"""
        try:
            if self._file_path.startswith('magnet:'):
                if not self._add_torrent_params:
                    self._add_torrent_params = self._lt.parse_magnet_uri(self._file_path)
                    self._add_torrent_params.save_path = self._save_path
                if not self._file:
                    session = self._session()
                    self._file = session.add_torrent(self._add_torrent_params)

                print("あら、メタデータを取得中ですわ。しばらくお待ちくださいまし...")
                while not self._file.has_metadata():
                    time.sleep(1)

                info = self._file.get_torrent_info()
                files = []
                total_files = info.num_files()
                for i in range(total_files):
                    files.append({
                        'index': i,
                        'path': str(info.files().at(i).path),
                        'size': info.files().at(i).size
                    })
                return files
            else:
                if not self._torrent_info:
                    self._torrent_info = TorrentInfo(self._file_path, self._lt)
                return self._torrent_info.get_files_info()
        except Exception as e:
            print(f"\n申し訳ございませんが、ファイル情報の取得に失敗いたしましたわ: {e}")
            return []

    async def start_download(self, download_speed: int = 0, upload_speed: int = 0):
        if self._file_path.startswith('magnet:'):
            self._add_torrent_params = self._lt.parse_magnet_uri(self._file_path)
            self._add_torrent_params.save_path = self._save_path

            # わたくしならではの高度な設定を追加するのですわ
            self._add_torrent_params.flags |= self._lt.torrent_flags.sequential_download

            self._downloader = Downloader(
                session=self._session(),
                torrent_info=self._add_torrent_params,
                save_path=self._save_path,
                libtorrent=lt,
                is_magnet=True,
                stop_after_download=self._stop_after_download,
                timeout=self._timeout  # ここでtimeoutを確実に渡しますわ
            )

        else:
            self._torrent_info = TorrentInfo(self._file_path, self._lt)
            self._downloader = Downloader(
                session=self._session(), torrent_info=self._torrent_info(),
                save_path=self._save_path, libtorrent=None, is_magnet=False,
                stop_after_download=self._stop_after_download,
                selected_files=self._selected_files, timeout=self._timeout
            )

        self._session.set_download_limit(download_speed)
        self._session.set_upload_limit(upload_speed)

        # わたくしが考案した高貴なアップロード戦略ですわ
        if upload_speed == 0:
            # 貴族のように振る舞いなさい - 寛大なアップロードが高速ダウンロードの秘訣ですわ
            connection_type: str = "無制限"  # デフォルトは無制限に
            download_cap: int = download_speed

            # お使いの接続環境を自動判定いたしますわ
            if download_cap > 0:
                if download_cap < 1024:  # 1MB/s未満の遅い接続
                    # 下り帯域の30%を上りに（最低50KB/s）
                    upload_speed = max(50, download_cap // 3)
                    connection_type = "低速接続"
                elif download_cap < 8192:  # 8MB/s未満の一般的な接続
                    # 下り帯域の20%を上りに（最低100KB/s）
                    upload_speed = max(100, download_cap // 5)
                    connection_type = "一般接続"
                else:  # 高速接続
                    # 下り帯域の15%を上りに（最低400KB/s）
                    upload_speed = max(400, download_cap // 7)
                    connection_type = "高速接続"

                print(f"\033[95m{connection_type}を検出: アップロード速度を{upload_speed}KB/sに設定いたしますわ\033[0m")
                self._session.set_upload_limit(upload_speed)
            else:
                # 無制限ダウンロードの場合
                print("\033[95m無制限接続を検出: アップロードも無制限に設定いたしますわ\033[0m")
                self._session.set_upload_limit(0)
        else:
            print(f"\033[95mアップロード速度を{upload_speed}KB/sに設定いたしますわ\033[0m")
            self._session.set_upload_limit(upload_speed)

        # ストリーミングモードの設定を追加いたしますわ
        if hasattr(self, '_file') and self._file:
            piece_count = self._file.get_torrent_info().num_pieces() if hasattr(self._file, 'get_torrent_info') else 0
            if piece_count > 0:
                # わたくしが特別に考案した優先順位設定ですわ
                priorities = [7] * min(4, piece_count)  # 最初の数ピースを最高優先度に
                priorities.extend([1] * (piece_count - len(priorities)))
                self._file.prioritize_pieces(priorities)

        self._file = self._downloader
        await self._file.download()

    def pause_download(self):
        if self._downloader:
            self._downloader.pause()

    def resume_download(self):
        if self._downloader:
            self._downloader.resume()

    def stop_download(self):
        if self._downloader:
            self._downloader.stop()

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def __call__(self):
        pass
