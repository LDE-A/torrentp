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
        # より高貴な設定にいたしますわ
        settings = {
            'listen_interfaces': f'{self._listen_interfaces}:{self._port}',
            'user_agent': self._user_agent,
            'connections_limit': 500,  # 200→500に引き上げますわ！平民でも多くの従者を持つべきですわ
            'connection_speed': 200,   # 50→200へ！まるで貴族の馬車のようですわね
            'peer_connect_timeout': 10,  # 15→10へ。時間は貴重ですもの
            'request_timeout': 5,      # 10→5へ。待ち時間など無駄ですわ
            'alert_mask': self._lt.alert.category_t.all_categories,
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'announce_to_all_trackers': True,
            'announce_to_all_tiers': True,
            'download_rate_limit': self._download_rate_limit,
            'upload_rate_limit': self._upload_rate_limit,
            # トラッカーへの接続頻度を上げて、より多くのピアを集めるのですわ
            'tracker_completion_timeout': 30,  # 秒単位
            'tracker_receive_timeout': 10,
            'stop_tracker_timeout': 5,
            'udp_tracker_token_expiry': 60,
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
