# scripts/upload_release.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from utils.upload_tools import do_final_dump_and_upload

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    print(f"⏳ 等待 5 分钟后开始上传 ➜ {playtype}")
    time.sleep(5 * 60)  # 延迟 5 分钟
    print(f"🚀 正在上传 Release ➜ {playtype}")
    do_final_dump_and_upload(playtype)
