# scripts/run_all.py
import os, sys
import subprocess
import threading
import re
from time import sleep, time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)  # 切换到项目根目录

# 上传间隔（单位：秒）
UPLOAD_INTERVAL = 60 * 60  # 每 60 分钟自动上传一次

def run_command(cmd, capture=False):
    print(f"\n🟢 执行: {cmd}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if capture:
        result = subprocess.run(
            cmd,
            shell=not isinstance(cmd, list),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=env
        )
    else:
        result = subprocess.run(
            cmd,
            shell=not isinstance(cmd, list),
            env=env
        )

    if result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        if capture:
            print(f"命令输出：{result.stdout}")
        sys.exit(result.returncode)
    return result


def start_upload_timer(playtype, interval_sec):
    def upload_loop():
        while True:
            sleep(interval_sec)
            print(f"\n🕓 [定时上传线程] 已达 {interval_sec // 60} 分钟 ➜ 执行 upload_release.py")
            run_command([sys.executable, "scripts/upload_release.py", playtype])
    threading.Thread(target=upload_loop, daemon=True).start()


if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "gewei_sha3"

    # ✅ 启动后台上传线程
    start_upload_timer(playtype, UPLOAD_INTERVAL)

    while True:
        print("\n📌 === STEP 1: 生成任务 ===")
        gen_result = run_command([sys.executable, "scripts/generate_tasks.py", playtype], capture=True)
        gen_output = gen_result.stdout
        print(gen_output)

        no_new_task = "🟢 没有新任务插入 ➜ 外层可退出" in gen_output

        print("\n📌 === STEP 2: 回测任务 ===")

        # ✅ 实时打印 + 收集输出
        backtest_output_lines = []
        process = subprocess.Popen(
            [sys.executable, "-u", "scripts/backtest.py", playtype],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8"
        )

        for line in process.stdout:
            print(line, end="")            # ✅ 实时打印
            backtest_output_lines.append(line)

        process.wait()
        backtest_output = "".join(backtest_output_lines)

        # ✅ 提取“待执行任务数量”
        match = re.search(r"待执行任务[:：]\s*(\d+)", backtest_output)
        pending_count = int(match.group(1)) if match else -1
        print(f"📊 当前待执行任务数量: {pending_count}")

        # ✅ 判断是否还有任务
        no_pending_task = pending_count == 0

        if no_new_task and no_pending_task:
            print("\n✅ 没有新任务且没有可执行任务 ➜ 主流程收工退出")
            run_command([sys.executable, "scripts/upload_release.py", playtype])
            break

        print("\n⏳ 还有任务或有新组合 ➜ 等待下一轮...")
        sleep(1)
