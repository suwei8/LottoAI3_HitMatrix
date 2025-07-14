# utils/upload_tools.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
import shlex
from sqlalchemy import text
from utils.db import get_engine
from datetime import datetime
from zoneinfo import ZoneInfo  # ✅ 新增

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
    engine = get_engine()
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")
    GH_TOKEN = os.getenv("GH_TOKEN")

    # ✅ 注入 GitHub token 到环境变量
    os.environ["GH_TOKEN"] = GH_TOKEN
    os.environ["GITHUB_TOKEN"] = GH_TOKEN

    tag = f"p5_{playtype_en}"
    zip_name = f"lotto_ai3_hitmatrix_p5_{playtype_en}.sql.zip"

    # ✅ 第一步：导出数据表
    dump_cmd = (
        f"mysqldump "
        f"-h {MYSQL_HOST} -u{MYSQL_USER} -p\"{MYSQL_PASSWORD}\" "
        f"--skip-triggers "
        f"--set-gtid-purged=OFF "
        f"--column-statistics=0 "
        f"--add-drop-table "
        f"--default-character-set=utf8mb4 "
        f"--single-transaction "
        f"--quick "
        f"{MYSQL_DATABASE} tasks best_tasks best_ranks > tasks_best.sql"
    )
    run_command(dump_cmd, use_shell=True)


    # ✅ 第二步：压缩 SQL 文件
    import pyminizip  # 确保你已在 requirements.txt 中添加

    # ✅ 使用 pyminizip 进行加密压缩
    src_file = "tasks_best.sql"
    zip_file = zip_name
    password = BACKUP_PASSWORD
    compression_level = 5  # 范围 1（最快）~ 9（最高压缩比）

    pyminizip.compress(src_file, None, zip_file, password, compression_level)
    print(f"✅ 已使用 pyminizip 压缩加密 ➜ {zip_file}")

    # ✅ 第三步：删除已有 release（如果存在）
    delete_cmd = (
        f"gh release delete {tag} --yes "
        f"--repo suwei8/LottoAI3_HitMatrix_date || echo '✅ 旧 release 不存在，跳过删除'"
    )
    run_command(delete_cmd, use_shell=True)

    # ✅ 第四步：创建新的 release（确保不会交互卡死）
    with engine.begin() as conn:
        total_tasks = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        done_tasks = conn.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'done'")).scalar()
        best_tasks = conn.execute(text("SELECT COUNT(*) FROM best_tasks")).scalar()
        now_str = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        notes = (
            f"📊 上传时间：{now_str}"
            f"🧮 任务总数：{total_tasks}"
            f"🎯 命中任务：{done_tasks}"
            f"🏅 高等级任务：{best_tasks}"
        )
        create_cmd = (
            f"gh release create {tag} "
            f"--repo suwei8/LottoAI3_HitMatrix_date "
            f"--title {tag} "
            f"--notes \"{notes}\""
        )
        run_command(create_cmd, use_shell=True)

    # ✅ 第五步：上传 zip 文件
    upload_cmd = (
        f"gh release upload {tag} {zip_name} "
        f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
    )
    run_command(upload_cmd, use_shell=True)