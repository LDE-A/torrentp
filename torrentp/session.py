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
        # 高貴なわたくしからの高性能設定を施してさしあげますわ
        settings = {
            'listen_interfaces': f'{self._listen_interfaces}:{self._port}',
            'user_agent': self._user_agent,
            'connections_limit': 200,  # 同時接続数の制限
            'connection_speed': 50,    # 接続速度の設定
            'peer_connect_timeout': 15,  # ピア接続タイムアウト
            'request_timeout': 10,     # リクエストタイムアウト
            'alert_mask': self._lt.alert.category_t.all_categories,
            'enable_dht': True,        # DHTを有効に
            'enable_lsd': True,        # ローカルサービスディスカバリを有効に
            'enable_upnp': True,       # UPNPを有効に
            'enable_natpmp': True,     # NAT-PMPを有効に
            'announce_to_all_trackers': True,  # すべてのトラッカーにアナウンス
            'announce_to_all_tiers': True,     # すべての階層にアナウンス
            'download_rate_limit': self._download_rate_limit,
            'upload_rate_limit': self._upload_rate_limit,
        }
        self._session = self._lt.session(settings)
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
