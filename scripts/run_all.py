# scripts/run_all.py
import os, sys
import subprocess
from time import sleep, time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)  # 切换到项目根目录

MAX_DURATION = 5 * 60  # 🧪 测试用：最多运行 5 分钟
start_time = time()

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
        print(f"命令输出：{result.stdout}")
        sys.exit(result.returncode)
    return result

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "gewei_sha3"

    while True:
        print("\n📌 === STEP 1: 生成任务 ===")
        gen_result = run_command([sys.executable, "scripts/generate_tasks.py", playtype], capture=True)
        gen_output = gen_result.stdout
        print(gen_output)

        no_new_task = "🟢 没有新任务插入 ➜ 外层可退出" in gen_output

        print("\n📌 === STEP 2: 回测任务 ===")
        backtest_result = run_command([sys.executable, "scripts/backtest.py"], capture=True)
        backtest_output = backtest_result.stdout
        print(backtest_output)

        no_pending_task = "待执行任务: 0" in backtest_output

        elapsed = time() - start_time

        # ✅ 到达时限 ➜ 启动 upload_release.py 作为后台子进程
        if elapsed > MAX_DURATION:
            print(f"\n⏰ 已达最大执行时长 {MAX_DURATION / 60:.1f} 分钟 ➜ 启动延迟上传任务")
            subprocess.Popen(
                [sys.executable, "scripts/upload_release.py", playtype],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            break

        # ✅ 没有新任务 且 没有待执行任务 ➜ 也启动上传
        if no_new_task and no_pending_task:
            print("\n✅ 没有新任务且没有可执行任务 ➜ 启动上传任务并退出")
            subprocess.Popen(
                [sys.executable, "scripts/upload_release.py", playtype],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            break

        print("\n⏳ 还有任务或有新组合 ➜ 等待下一轮...")
        sleep(1)
