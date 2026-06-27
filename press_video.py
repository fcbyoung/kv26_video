# 用于批量压缩本地视频文件
# 在尽可能保留足够视频分辨率(720P)的条件下，通过降低码率等其他方式，使得视频文件总体大小可以进一步得到压缩

import os
import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

# ================== 配置参数 ==================
INPUT_DIR = "E:\\movie"
OUTPUT_DIR = "E:\\press_video"
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".flv")
TARGET_RES = "720"
VIDEO_BITRATE = "1.5M"
AUDIO_BITRATE = "128k"
FFMPEG_CMD = "ffmpeg"
MAX_WORKERS = 3
# ==============================================


def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def compress_video(input_path, output_path):
    vf = f"scale=-2:{TARGET_RES}"
    cmd = [
        FFMPEG_CMD, "-i", str(input_path),
        "-threads", "4",
        "-preset", "faster",
        "-c:v", "libx264",
        "-vf", vf,
        "-b:v", VIDEO_BITRATE,
        "-maxrate", "2M", "-bufsize", "3M",
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-movflags", "+faststart",
        "-y", str(output_path)
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        return True
    except subprocess.CalledProcessError:
        return False


def process_one_video(video_file, status_dict):
    """处理单个视频：压缩 + 返回元数据，并输出提示信息"""
    output_path = Path(OUTPUT_DIR) / f"{video_file.stem}_720p.mp4"

    if output_path.exists():
        status_dict["skipped"] += 1
        tqdm.write(f"跳过已存在: {output_path.name}")
        return {"type": "skip", "data": None}

    tqdm.write(f"开始压缩: {video_file.name}")
    start_time = time.time()
    success = compress_video(video_file, output_path)
    elapsed = time.time() - start_time

    if success:
        status_dict["processed"] += 1
        tqdm.write(f"完成压缩: {output_path.name} (耗时 {elapsed:.1f}秒)")
        metadata = {
            "id": video_file.stem,
            "title": video_file.stem,
            "date": datetime.fromtimestamp(video_file.stat().st_mtime).strftime("%Y-%m-%d"),
            "video_url": f"https://your-bucket.r2.dev/videos/{output_path.name}"
        }
        return {"type": "success", "data": metadata}
    else:
        status_dict["failed"] = status_dict.get("failed", 0) + 1
        tqdm.write(f"压缩失败: {video_file.name}")
        return {"type": "fail", "data": None}


def main():
    ensure_dirs()
    video_files = [f for f in Path(INPUT_DIR).iterdir() if f.suffix.lower() in VIDEO_EXTENSIONS]
    if not video_files:
        print(f"未在 {INPUT_DIR} 中找到视频文件")
        return

    print(f"找到 {len(video_files)} 个视频，使用 {MAX_WORKERS} 个线程并行压缩\n")

    status = {"processed": 0, "skipped": 0, "failed": 0}
    metadata_list = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_one_video, v, status): v for v in video_files}
        with tqdm(total=len(futures), desc="总体进度", unit="个", position=0) as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result["type"] == "success":
                    metadata_list.append(result["data"])
                pbar.update(1)
                pbar.set_postfix(
                    processed=status["processed"],
                    skipped=status["skipped"],
                    failed=status["failed"]
                )

    metadata_list.sort(key=lambda x: x["id"])

    # with open(VIDEOS_JSON, "w", encoding="utf-8") as f:
    #     json.dump(metadata_list, f, indent=2, ensure_ascii=False)

    print("\n" + "="*50)
    print(f"   所有任务完成！")
    print(f"   新压缩: {status['processed']} 个")
    print(f"   跳过:   {status['skipped']} 个")
    print(f"   失败:   {status['failed']} 个")
    print(f"   压缩视频保存在: {OUTPUT_DIR}")
    print("="*50)


if __name__ == "__main__":
    main()
