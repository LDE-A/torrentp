class TorrentInfo:
    def __init__(self, path, libtorrent):
        self._path = path
        self._lt = libtorrent
        self._info = self._lt.torrent_info(self._path)

    def show_info(self):
        pass

    def create_torrent_info(self):
        self._info = self._lt.torrent_info(self._path)
        return self._info

    def get_files_info(self):
        """わたくしがトレントファイルの情報を取得させていただきますわ"""
        files = []
        if self._info.num_files() > 0:
            for i in range(self._info.num_files()):
                file_entry = self._info.files().file_entry(i)
                files.append({
                    'index': i,
                    'path': file_entry.path,
                    'size': file_entry.size
                })
        return files

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def __call__(self):
        return self.create_torrent_info()
