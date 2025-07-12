# scripts/upload_release.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.upload_tools import do_final_dump_and_upload

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    print(f"🚀 开始上传 GitHub Release ➜ {playtype}")
    do_final_dump_and_upload(playtype)
