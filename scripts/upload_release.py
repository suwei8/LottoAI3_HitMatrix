# scripts/upload_release.py
import sys, os
import time
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.upload_tools import do_final_dump_and_upload

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "unknown"

    print(f"⏳ 等待 5.5 小时后开始上传 ➜ {playtype}")
    time.sleep(5.5 * 60 * 60)  # 延时 5.5 小时（19800 秒）

    print(f"🚀 正在上传 Release ➜ {playtype}")
    do_final_dump_and_upload(playtype)

    print("📢 正在发送企业微信通知...")
    result = subprocess.run(
        [sys.executable, "scripts/send_notify.py", playtype],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print(f"✅ 企业微信通知发送状态码: {result.returncode}")
