# scripts/run_all.py
import os, sys
import subprocess
from time import sleep

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(PROJECT_ROOT)  # 切换到项目根

def run_command(cmd, capture=False):
    print(f"\n🟢 执行: {cmd}")
    if capture:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, encoding="utf-8"
        )
    else:
        result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        sys.exit(result.returncode)
    return result

if __name__ == "__main__":
    playtype = sys.argv[1] if len(sys.argv) > 1 else "千位定1"

    while True:
        print("\n📌 === STEP 1: 生成任务 ===")
        gen_result = run_command(f"python scripts/generate_tasks.py {playtype}", capture=True)
        gen_output = gen_result.stdout
        print(gen_output)

        no_new_task = "🟢 没有新任务插入 ➜ 外层可退出" in gen_output

        print("\n📌 === STEP 2: 回测任务 ===")
        backtest_result = run_command("python scripts/backtest.py", capture=True)
        backtest_output = backtest_result.stdout
        print(backtest_output)

        no_pending_task = "待执行任务: 0" in backtest_output

        if no_new_task and no_pending_task:
            print("\n✅ 没有新任务且没有可执行任务 ➜ 已完成！")
            break

        print("\n⏳ 还有任务或有新组合 ➜ 等待下一轮...")
        sleep(1)
