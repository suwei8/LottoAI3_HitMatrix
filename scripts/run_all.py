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

    # === 中文 ➜ 拼音映射表 ===
    PLAYTYPE_MAP = {
        "万位杀3": "wanwei_sha3",
        "万位杀1": "wanwei_sha1",
        "万位定5": "wanwei_ding5",
        "万位定3": "wanwei_ding3",
        "万位定1": "wanwei_ding1",
        "千位杀3": "qianwei_sha3",
        "千位杀1": "qianwei_sha1",
        "千位定5": "qianwei_ding5",
        "千位定3": "qianwei_ding3",
        "千位定1": "qianwei_ding1",
        "百位杀3": "baiwei_sha3",
        "百位杀1": "baiwei_sha1",
        "百位定5": "baiwei_ding5",
        "百位定3": "baiwei_ding3",
        "百位定1": "baiwei_ding1",
        "十位杀3": "shiwei_sha3",
        "十位杀1": "shiwei_sha1",
        "十位定5": "shiwei_ding5",
        "十位定3": "shiwei_ding3",
        "十位定1": "shiwei_ding1",
        "个位杀3": "gewei_sha3",
        "个位杀1": "gewei_sha1",
        "个位定5": "gewei_ding5",
        "个位定3": "gewei_ding3",
        "个位定1": "gewei_ding1",
    }

    playtype_en = PLAYTYPE_MAP.get(playtype)
    if not playtype_en:
        print(f"❌ 未找到拼音映射: {playtype}")
        sys.exit(1)

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

    # === Dump & Upload (固定名 + 拼音 Tag) ===
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
        f"gh release create p5_{playtype_en} "
        f"--repo suwei8/LottoAI3_HitMatrix_date "
        f"--title 'p5_{playtype_en}' || echo 'Release already exists'"
    )

    upload_cmd = (
        f"gh release upload p5_{playtype_en} tasks_best.zip "
        f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
    )

    run_command(dump_cmd)
    run_command(zip_cmd)
    run_command(create_cmd)
    run_command(upload_cmd)

    print(f"🎉 Dump & Upload 完成 ➜ tasks_best.zip 已上传（覆盖）")
