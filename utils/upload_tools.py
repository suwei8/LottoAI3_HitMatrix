import sys, os
import subprocess
import shlex
from datetime import datetime
from sqlalchemy import text
from utils.db import get_engine  # ✅ 使用项目内已有数据库连接函数

def run_command(cmd, capture=False, use_shell=False):
    print(f"\n🟢 执行: {cmd}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if capture:
        if use_shell:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                env=env
            )
        else:
            result = subprocess.run(
                cmd if isinstance(cmd, list) else shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                env=env
            )
    else:
        if use_shell:
            result = subprocess.run(cmd, shell=True, env=env)
        else:
            result = subprocess.run(cmd if isinstance(cmd, list) else shlex.split(cmd), env=env)

    if result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        print("命令输出：", result.stdout)
        sys.exit(result.returncode)
    return result

def do_final_dump_and_upload(playtype_en):
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

    run_command(dump_cmd, use_shell=True)
    run_command(zip_cmd, use_shell=True)

    # 📊 生成上传说明
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            task_count = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
            qualified_count = conn.execute(text("SELECT COUNT(*) FROM best_tasks")).scalar()
            level_count = conn.execute(text("SELECT COUNT(*) FROM best_ranks")).scalar()
    except Exception as e:
        print(f"⚠️ 数据库连接失败，描述内容将简化: {e}")
        task_count = qualified_count = level_count = "N/A"

    notes = (
        f"📊 上传时间：{now_str}\n"
        f"🧮 任务总数：{task_count}\n"
        f"🎯 命中任务：{qualified_count}\n"
        f"🏅 高等级任务：{level_count}"
    )

    # 🆕 创建 Release（如已存在则跳过）
    create_cmd = (
        f"gh release create p5_{playtype_en} "
        f"--repo suwei8/LottoAI3_HitMatrix_date "
        f"--title 'p5_{playtype_en}' "
        f"--notes \"{notes}\" || echo 'Release already exists'"
    )
    run_command(create_cmd, use_shell=True)

    # 上传文件
    upload_cmd = (
        f"gh release upload p5_{playtype_en} {zip_name} "
        f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
    )
    run_command(upload_cmd, use_shell=True)
