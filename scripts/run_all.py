# scripts/run_all.py
import os, sys
import subprocess
from time import time, sleep
from utils.db import PLAYTYPE_MAPPING

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(PROJECT_ROOT)  # 切换到项目根

MAX_DURATION = 5.5 * 60 * 60  # 单位：秒，5.5 小时
start_time = time()

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
    playtype_en = sys.argv[1] if len(sys.argv) > 1 else "qianwei_ding1"
    playtype_cn = PLAYTYPE_MAPPING.get(playtype_en)

    if not playtype_cn:
        print(f"❌ 未找到中文映射: {playtype_en}")
        sys.exit(1)

    while True:
        print("\n📌 === STEP 1: 生成任务 ===")
        gen_result = run_command(f"python scripts/generate_tasks.py \"{playtype_cn}\"", capture=True)
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

            # === Dump & Upload 只在到点时执行 ===
            MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
            MYSQL_USER = os.getenv("MYSQL_USER", "root")
            MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
            MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
            BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")

            dump_cmd = (
                f"mysqldump -h {MYSQL_HOST} -u{MYSQL_USER} -p\"{MYSQL_PASSWORD}\" "
                f"{MYSQL_DATABASE} tasks best_tasks best_ranks > tasks_best.sql"
            )

            zip_name = f"lotto_ai3_hitmatrix_p5_{playtype_en}.sql.zip"
            zip_cmd = f"zip -P {BACKUP_PASSWORD} {zip_name} tasks_best.sql"

            run_command(dump_cmd)
            run_command(zip_cmd)

            create_cmd = (
                f"gh release create p5_{playtype_en} "
                f"--repo suwei8/LottoAI3_HitMatrix_date "
                f"--title 'p5_{playtype_en}' || echo 'Release already exists'"
            )
            run_command(create_cmd)

            upload_cmd = (
                f"gh release upload p5_{playtype_en} {zip_name} "
                f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
            )
            run_command(upload_cmd)


            break  # ✅ 一定要放这里


        if no_new_task and no_pending_task:
            print("\n✅ 没有新任务且没有可执行任务 ➜ 已完成！")
            break

        print("\n⏳ 还有任务或有新组合 ➜ 等待下一轮...")
        sleep(1)