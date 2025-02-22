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
        self._add_torrent_params = None
        self._is_magnet = is_magnet
        self._paused = False
        self._stop_after_download = stop_after_download
        self._selected_files = selected_files
        self._timeout = timeout  # デフォルトで5分のタイムアウトを設定いたしますわ
        self._last_progress = 0
        self._last_progress_time = time.time()
        self._download_started = False  # ダウンロードが開始されたかどうかを追跡いたしますわ

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
            self._last_progress_time = time.time()  # 初期時刻を設定いたしますわ

            while not self._status.is_seeding:
                if not self._paused:
                    status = self.status()
                    self._get_status_progress(status)
                    self._check_timeout(status.progress)
                    sys.stdout.flush()

                await asyncio.sleep(1)

            if self._stop_after_download:
                self.stop()
            else:
                print('\033[92m' + "\nDownloaded successfully." + '\033[0m')

        except DownloadTimeoutError as e:
            self.stop()
            raise e
        except Exception as e:
            self._cleanup_files()
            self.stop()
            raise Exception(f"\nダウンロード中に予期せぬ問題が発生いたしましたわ: {e}")

    def _get_status_progress(self, s):
        _percentage = s.progress * 100
        _download_speed = s.download_rate / 1000 / 1000
        _upload_speed = s.upload_rate / 1000

        counting = math.ceil(_percentage / 5)
        visual_loading = '#' * counting + ' ' * (20 - counting)
        _message = "\r\033[42m %.2f mb/s \033[0m|\033[46m up: %.1f Kb/s \033[0m| status: %s | peers: %d  \033[96m|%s|\033[0m %d%%" % (_download_speed, _upload_speed, s.state, s.num_peers, visual_loading, _percentage)
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
