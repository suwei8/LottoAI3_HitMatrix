# scripts/run_all.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
import subprocess
from time import sleep, time

from utils.upload_tools import do_final_dump_and_upload  # 👈 必须有
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)  # 切换到项目根

MAX_DURATION = 5.5 * 60 * 60  # 单位：秒
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
    playtype = sys.argv[1] if len(sys.argv) > 1 else "千位定1"

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

        # ✅ 只要到点 ➜ 做收尾
        if elapsed > MAX_DURATION:
            print(f"\n⏰ 已达最大执行时长 {MAX_DURATION/60:.1f} 分钟 ➜ 强制收工")
            do_final_dump_and_upload(playtype)
            break

        # ✅ 如果没有新任务 + 没有待执行任务 ➜ 也收尾
        if no_new_task and no_pending_task:
            print("\n✅ 没有新任务且没有可执行任务 ➜ 做收尾并退出")
            do_final_dump_and_upload(playtype)
            break

        print("\n⏳ 还有任务或有新组合 ➜ 等待下一轮...")
        sleep(1)
