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
            file_storage = self._info.files()
            for i in range(self._info.num_files()):
                files.append({
                    'index': i,
                    'path': file_storage.file_path(i),
                    'size': file_storage.file_size(i)
                })
        return files

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def __call__(self):
        return self.create_torrent_info()
