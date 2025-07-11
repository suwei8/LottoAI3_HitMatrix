# scripts/run_all.py

import os, sys
import subprocess
from time import sleep, time
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(PROJECT_ROOT)

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

    MAX_DURATION = 5.5 * 60 * 60
    start_time = time()

    while True:
        print("\n📌 === STEP 1: 生成任务 ===")
        gen_result = run_command(f"python scripts/generate_tasks.py \"{playtype}\"", capture=True)
        gen_output = gen_result.stdout
        print(gen_output)

        no_new_task = "🟢 没有新任务插入 ➜ 外层可退出" in gen_output

        print("\n📌 === STEP 2: 回测任务 ===")
        backtest_result = run_command("python scripts/backtest.py", capture=True)
        backtest_output = backtest_result.stdout
        print(backtest_output)

        no_pending_task = "待执行任务: 0" in backtest_output

        elapsed = time() - start_time
        if elapsed > MAX_DURATION:
            print(f"\n⏰ 已达最大执行时长 {MAX_DURATION/60:.1f} 分钟 ➜ 强制收工")
            break

        if no_new_task and no_pending_task:
            print("\n✅ 没有新任务且没有可执行任务 ➜ 已完成！")
            break

        print("\n⏳ 还有任务或有新组合 ➜ 等待下一轮...")
        sleep(1)

    # === Dump & Upload (固定名 + 覆盖) ===
    print("\n📦 正在备份 tasks & best_tasks...")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")

    dump_cmd = (
        f"mysqldump -h {MYSQL_HOST} -u{MYSQL_USER} -p\"{MYSQL_PASSWORD}\" "
        f"{MYSQL_DATABASE} tasks best_tasks > tasks_best.sql"
    )
    zip_cmd = f"zip -P {BACKUP_PASSWORD} tasks_best.zip tasks_best.sql"

    # 如果 Release 不存在则先创建
    create_cmd = (
        f"gh release create p5_{playtype} "
        f"--repo suwei8/LottoAI3_HitMatrix_date "
        f"--title 'p5_{playtype}' || echo 'Release already exists'"
    )

    upload_cmd = (
        f"gh release upload p5_{playtype} tasks_best.zip "
        f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
    )

    run_command(dump_cmd)
    run_command(zip_cmd)
    run_command(create_cmd)
    run_command(upload_cmd)

    print(f"🎉 Dump & Upload 完成 ➜ tasks_best.zip 已上传（覆盖）")
