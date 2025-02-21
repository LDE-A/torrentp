!pip install libtorrent-python asyncclick

# GitHubからプロジェクトをクローン
!git clone <your_repository_url> /content/torrentp

# Python pathに追加して、モジュールとして認識させる
import sys
sys.path.append('/content')

# これで以下のようにインポートが可能になりますわ
from torrentp.torrentp.torrent_downloader import TorrentDownloader

# 使用例
import asyncio
import nest_asyncio
nest_asyncio.apply()

torrent = TorrentDownloader("example.torrent", ".")
files = torrent.get_files_info()
print("ご確認ください、トレント内のファイル一覧でございます:")
for file in files:
    print(f"{file['index']}: {file['path']} ({file['size']} bytes)")

# ダウンロードしたいファイルのインデックスを選択
selected_indices = [0, 2]  # 例：0番目と2番目のファイルのみをダウンロード

# 選択したファイルのみをダウンロード
torrent = TorrentDownloader("example.torrent", ".", selected_files=selected_indices)
await torrent.start_download()