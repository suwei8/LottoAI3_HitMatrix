import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

os.environ["GH_TOKEN"] = os.getenv("GH_TOKEN", "")

import subprocess

from utils.upload_tools import do_final_dump_and_upload

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    print(f"\n🕒 启动上传任务 ➜ {playtype}")
    do_final_dump_and_upload(playtype)

    print("\n📢 正在发送企业微信通知...")
    result = subprocess.run(
        [sys.executable, "scripts/send_notify.py", playtype],
        capture_output=True,
        text=True,
        encoding="utf-8",  # ✅ 显式指定编码
        errors="replace"   # ✅ 防止乱码直接报错
    )
    print(result.stdout)
    print(f"✅ 企业微信通知发送状态码: {result.returncode}")
