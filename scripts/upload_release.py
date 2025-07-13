# scripts/upload_release.py

import sys, os
import time
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.upload_tools import do_final_dump_and_upload

def send_wechat_notify(playtype):
    print("📢 正在发送企业微信通知...")
    result = subprocess.run(
        [sys.executable, "scripts/send_notify.py", playtype],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    print(f"✅ 企业微信通知发送状态码: {result.returncode}")

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    print(f"📡 每 5 分钟上传一次 Release ➜ {playtype}")

    try:
        while True:
            print(f"\n🕒 {time.strftime('%Y-%m-%d %H:%M:%S')} ➜ 正在上传 Release")
            do_final_dump_and_upload(playtype)
            send_wechat_notify(playtype)
            print(f"⏳ 等待 5 分钟后继续上传...")
            time.sleep(5 * 60)
    except KeyboardInterrupt:
        print("\n🛑 已终止上传循环")
