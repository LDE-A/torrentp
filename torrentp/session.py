class Session:
    def __init__(self, libtorrent, port='6881'):
        self._user_agent = 'python client v0.1'
        self._listen_interfaces = '0.0.0.0'
        self._port = port
        self._download_rate_limit = 0
        self._upload_rate_limit = 0
        self._lt = libtorrent
        self._session = None

    def create_session(self):
        # より高貴でバージョン互換性のある設定にいたしますわ
        settings = {
            'listen_interfaces': f'{self._listen_interfaces}:{self._port}',
            'user_agent': self._user_agent,
            'connections_limit': 500,  # 多くの従者を従えるのが貴族の嗜みですわ
            'connection_speed': 200,   # 速さは力ですのよ
            'peer_connect_timeout': 10,
            'request_timeout': 5,
            'alert_mask': self._lt.alert.category_t.all_categories,
            'enable_dht': True,        # 分散ハッシュテーブルは必須ですわ
            'enable_lsd': True,        # ローカルサービス検出も欠かせませんわね
            'enable_upnp': True,       # UPnPも有効に
            'enable_natpmp': True,     # NAT-PMPも使いますわよ
            'announce_to_all_trackers': True,
            'announce_to_all_tiers': True,
            'download_rate_limit': self._download_rate_limit,
            'upload_rate_limit': self._upload_rate_limit,
            'tracker_completion_timeout': 30,
            'tracker_receive_timeout': 10,
            'stop_tracker_timeout': 5,
            'udp_tracker_token_expiry': 60,
        }

        try:
            # 互換性を確保するための検証
            compatible_settings = {}
            for key, value in settings.items():
                try:
                    # キーが存在するか確認（平民のライブラリでも動作するように）
                    test_settings = {key: value}
                    test_session = self._lt.session(test_settings)
                    compatible_settings[key] = value
                except Exception:
                    # 不適合な設定は静かにスキップ
                    print(f"\033[93m警告: 設定'{key}'はお使いのlibtorrentでは対応していないようですわ。スキップいたしますわ\033[0m")
                    pass

            self._session = self._lt.session(compatible_settings)
        except Exception as e:
            # 完全にフォールバック
            print(f"\033[91mあら、お粗末なライブラリですわね。基本設定のみで初期化いたしますわ: {e}\033[0m")
            self._session = self._lt.session()

        return self._session

    def set_download_limit(self, rate=0):
        self._download_rate_limit = int(-1 if rate == 0 else (1 if rate == -1 else rate * 1024))
        self._session.set_download_rate_limit(self._download_rate_limit)

    def set_upload_limit(self, rate=0):
        self._upload_rate_limit = int(-1 if rate == 0 else (1 if rate == -1 else rate * 1024))
        self._session.set_upload_rate_limit(self._upload_rate_limit)

    def get_upload_limit(self):
        return self._session.upload_rate_limit()

    def get_download_limit(self):
        return self._session.download_rate_limit()

    def __str__(self):
        pass

    def __repr__(self):
        pass

    def __call__(self):
        return self.create_session()
