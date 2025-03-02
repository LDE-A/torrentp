#@title main
import sys
#sys.path.append('/usr/local/lib/python3.10/dist-packages')
from torrentp2.torrentp.torrent_downloader import TorrentDownloader
from torrentp2.torrentp.downloader import DownloadTimeoutError
import shutil
import os
import subprocess as sp
import pathlib
import discord_uploader
import math
import asyncio
from google.colab import userdata
import sqlite3
import nest_asyncio
nest_asyncio.apply()
import re
from datetime import datetime
import json
import time

_continue = False #@param {type:"boolean"}
_continue_anime_name = "謎の彼女X" #@param {type:"string"}
anime_txt_path = "animes_a.txt" #@param {type:"string"}
output_dir = "/content/anime_processing"
channel_ids = [1273360062211035156,1273360242364649563] #anime
#channel_ids = [1291259160406786160,1291259417194659935] #av
#TOKEN = os.environ.get("DISCORD_TOKEN")
TOKEN = userdata.get("ORIGINAL_TOKEN")
uploader = discord_uploader.DiscordUploader(TOKEN,0,use_native_method=False)
animes = []
with open(anime_txt_path, 'r') as f:
    for line in f:
        animes.append(line.strip())
include_exts = [".mp4",".mkv",".avi",".mov",".flv",".webm",".wmv",".asf",".vob",".mpg"]
db_path = "/content/danimes.db"
counter = 0
#conn = sqlite3.connect(db_path)
#cursor = conn.cursor()


def clean(text):
    exclude_words = ["720p", "1080p", "480p", "720P", "1080P", "4K", "480P", "H.264", "H.265", "h264", "h265", "H264", "H265", "h.264", "h.265", "WEB-DL"]
    # パターンを使って不要な部分を削除
    cleaned_string = re.sub(r'\[.*?\]|\(.*?\)', '', text)
    # Sx または Ex の形式を見つける
    episode_match = re.search(r'\b[S|E](\d{2})\b', cleaned_string)
    episode_number = episode_match.group(0) if episode_match else ''
    # 指定された文字列を消す
    for word in exclude_words:
        cleaned_string = re.sub(rf'\s*[\(\[]?\s*{re.escape(word)}\s*[\)\]]?\s*', ' ', cleaned_string)

    # タイトル部分を取得
    title_match = re.search(r'(.+)', cleaned_string.strip())
    if title_match:
        title = title_match.group(0).strip()
        title = title.rstrip('.mkv')
        # エピソード番号が存在する場合はタイトルに追加
        if episode_number:
            return f"{title}_{episode_number}.mkv"
        return text
    else:
        if cleaned_string.strip() != "":
            return cleaned_string.strip()
        else:
            return text


def try_remove(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def all_files_below_500MiB(directory):
    max_size = 500 * 1024 * 1024

    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_size = os.path.getsize(file_path)

            if file_size > max_size:
                return False
    return True


async def start_backup():
    line_num = 0
    for anime in animes:
        if _continue and line_num == 0:
            line_num += 1
            continue
        line_num += 1
        ret = await download_anime(anime)
        if ret is None:
            print(f"Timeout: {anime}")
            continue
        print(f"{line_num}/{len(animes)}")
        anime_name = anime.split(",")[1]
        target_dir = os.path.join(output_dir,os.listdir(output_dir)[0])
        if all_files_below_500MiB(target_dir) == False and contains_h264_codecs(target_dir):
            print(f"skipped {anime_name} Contains h264 video!")
            try_remove(target_dir)
            continue
        backup_anime_files(output_dir,anime_name)
        add_completed(anime)
        try_remove(output_dir)


def backup_anime_files(path,anime_name):
    if os.path.isdir(path):
        for file in sorted(os.listdir(path)):
            backup_anime_files(os.path.join(path,file),anime_name)
        if ".ipynb_checkpoints" not in path and "anime_processing" not in path:
            try_remove(path)
        uploader.use_native_method = True
        uploader.upload(db_path,1124573293387722802)
        uploader.use_native_method = False
    else:
        basename = os.path.basename(path)
        if "NCED" in basename or "NCOP" in basename:
            try_remove(path)
            return
        if any(basename.endswith(ext) for ext in include_exts):
            files = upload_video_in_chunks(path,anime_name)
            print(f"{basename} の送信完了")
            for f in files:
                try_remove(f)
        else:
            print(f"除外: {os.path.basename(path)}")
        try_remove(path)


async def download_anime(anime):
    url,anime_name = anime.split(",")
    print(f"starting download: {anime_name}")
    os.makedirs(output_dir, exist_ok=True)
    target = TorrentDownloader(url, output_dir,timeout=120)
    try:
        await target.start_download()
        return True
    except DownloadTimeoutError:
        print(f"Download timeout for {anime_name}")
        try:
            await target.start_download()
            return True
        except DownloadTimeoutError:
            try_remove(output_dir)
            return None


def add_completed(anime,_continue=False):
    with open(anime_txt_path, "r") as f:
        content = f.read()

    lines = content.splitlines()
    if _continue:
        new_lines = lines[1:]
    else:
        new_lines = [line for line in lines if line.strip().strip("\n") != anime.strip().strip("\n")]

    with open(anime_txt_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")
    uploader.use_native_method = True
    uploader.upload(anime_txt_path,1124573293387722802)
    uploader.upload(db_path,1124573293387722802)
    uploader.use_native_method = False


def insert_message_simple(m,file_name,anime_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO MESSAGES(
        id,content,created_at,file_name,file_size,anime_name)
        VALUES (?,?,?,?,?,?)""", (
            m["id"],
            m["content"],
            datetime.fromisoformat(m["timestamp"]),
            file_name,
            m["attachments"][0]["size"],
            anime_name
    ))
    conn.commit()
    conn.close()


def send_file(path,anime_name,sp_content=""):
    global counter
    sp_content = sp_content if sp_content.endswith("\n") else sp_content + "\n"
    path = path.strip().strip("\"")
    if os.path.exists(path) == False:
        print("ファイルが存在しません")
        return []
    if os.path.getsize(path) > 500*1024*1024:
        print("over 500")
        return []
    file_new_fullpath = os.path.join(os.path.dirname(path),clean(os.path.basename(path)))
    os.rename(path,file_new_fullpath)
    file_new_name = os.path.basename(file_new_fullpath)
    dir_name = os.listdir(output_dir)[0]
    content = f"{sp_content}{anime_name}"
    res = None
    for ch_id in channel_ids:
        try:
            ret = uploader.upload(file_new_fullpath,ch_id,f"{content}",include_filepath=True)
        except Exception as e:
            print(e)
            time.sleep(5)
            ret = uploader.upload(file_new_fullpath,ch_id,f"{content}",include_filepath=True)
        res = ret
        time.sleep(10)
    time.sleep(10)
    counter += 1
    insert_message_simple(res.json(),file_new_name,anime_name)
    print(f"[o] {file_new_fullpath}")
    return [file_new_fullpath]


def upload_video_in_chunks(file_path,anime_name):
    file_size = os.path.getsize(file_path)
    file_size_mib = file_size / (1024 * 1024)

    if file_size <= 500*1024*1024:
        return send_file(file_path,anime_name)
    elif file_size <= 100*1024*1024 and ("NCED" in file_path or "NCOP" in file_path):
        print("continue cuz this file is ncop or ed")
        return [file_path]
    else:
        split_num = 500 if file_size_mib <= 1500 else 400
        num_chunks = math.ceil(file_size / (split_num * 1024 * 1024)) #(file_size_mib / 450)
        return split_and_upload(file_path, num_chunks,anime_name)


def split_and_upload(file_path, num_chunks,anime_name):
    base_name, ext = os.path.splitext(os.path.basename(file_path))

    # 動画の全体の長さを取得（秒単位）
    total_duration = get_video_duration(file_path)
    if total_duration == 0:
        return []
    chunk_duration = total_duration / num_chunks

    files = []
    for i in range(num_chunks):
            start_time = i * chunk_duration
            output_file = os.path.join(output_dir, f"{base_name}_part{i+1}{ext}")

            cmd = [
                        "ffmpeg", "-i", file_path, "-ss", str(start_time), "-t", str(chunk_duration),
                        "-map", "0","-c", "copy", output_file
            ]
            try:
                sp.run(cmd, check=True)
            except Exception as e:
                cont = input(f"erro at split video using ffmpeg {e}\n{file_path}\ny/n:")
                if cont != "y":
                    try_remove(output_file)
                    return []
            send_file(output_file,anime_name,f"parts: {i+1}\n")
            files.append(output_file)
    return files


def get_video_duration(file_path):
    result = sp.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=sp.PIPE,
            stderr=sp.STDOUT
    )
    try:
        return float(result.stdout)
    except:
        return 0


def contains_h264_codecs(directory):
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                result = sp.run(
                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'json', file_path],
                    stderr=sp.PIPE,
                    stdout=sp.PIPE,
                    text=True
                )
                output = json.loads(result.stdout)
                if 'streams' in output:
                    for stream in output['streams']:
                        if stream.get('codec_name') == 'h264':
                            if os.path.getsize(file_path) <= 500*1024*1024:
                                return False
                            return True
            except Exception as e:
                print(f"Error processing file {filename}: {e}")
    return False



if _continue:
    backup_anime_files(output_dir,_continue_anime_name)
    add_completed(_continue_anime_name,_continue=True)
    try_remove(output_dir)

asyncio.run(start_backup())