# utils/upload_tools.py
import os
import sys
import subprocess
import shlex
import pyminizip  # ✅ 顶部引入
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from utils.db import get_engine  # ✅ 使用统一数据库封装
import tempfile

# ✅ 仅本地加载 .env，CI 不污染
from dotenv import load_dotenv
if os.getenv("GITHUB_ACTIONS") != "true":
    load_dotenv(override=False)


def run_command(cmd, capture=False, use_shell=False):
    print(f"\n🟢 执行: {cmd}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if capture:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else shlex.split(cmd),
            shell=use_shell,
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
            shell=use_shell,
            env=env
        )

    if result.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        if capture:
            print("命令输出：", result.stdout)
        sys.exit(result.returncode)

    return result


def do_final_dump_and_upload(playtype_en):
    # ✅ 显式读取并验证环境变量
    db_host = os.getenv("MYSQL_HOST", "127.0.0.1")
    db_user = os.getenv("MYSQL_USER", "root")
    db_password = os.getenv("MYSQL_PASSWORD")
    db_name = os.getenv("MYSQL_DATABASE")
    backup_password = os.getenv("BACKUP_PASSWORD")

    # ✅ 显示调试信息
    print("📌 环境变量检查:")
    print(f"  MYSQL_HOST = {db_host}")
    print(f"  MYSQL_USER = {db_user}")
    print(f"  MYSQL_PASSWORD = {'已设置' if db_password else '[未设置]'}")
    print(f"  MYSQL_DATABASE = {db_name if db_name else '[未设置]'}")
    print(f"  BACKUP_PASSWORD = {'已设置' if backup_password else '[未设置]'}")

    # ✅ 参数校验
    missing = []
    for k in ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE", "BACKUP_PASSWORD"]:
        if not os.getenv(k):
            missing.append(k)

    if missing:
        print(f"❌ 缺少以下环境变量：{', '.join(missing)}")
        print("🔍 请确认这些变量是否正确设置在 GitHub Actions 的 secrets 中")
        sys.exit(1)


    zip_name = f"lotto_ai3_hitmatrix_p5_{playtype_en}.sql.zip"

    # ✅ 1. 生成 mysqldump 命令
    dump_cmd = (
        f'mysqldump -h {db_host} -u{db_user} -p"{db_password}" '
        f'{db_name} tasks best_tasks best_ranks > tasks_best.sql'
    )
    run_command(dump_cmd, use_shell=True)

    import time
    print("✅ mysqldump 执行完成，准备压缩...")
    time.sleep(0.5)
    # ✅ 2. zip 压缩备份（跨平台方式）
    try:
        pyminizip.compress("tasks_best.sql", None, zip_name, backup_password, 5)
        print(f"✅ 使用 pyminizip 压缩成功 ➜ {zip_name}")
    except Exception as e:
        print(f"❌ 压缩失败: {e}")
        sys.exit(1)

    # ✅ 3. 获取上传描述（使用 get_engine 获取数据库连接）
    # 获取北京时间（UTC+8）
    now_bj = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=8)
    now_str = now_bj.strftime("%Y-%m-%d %H:%M:%S")

    try:
        engine = get_engine()
        with engine.connect() as conn:
            task_count = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
            qualified_count = conn.execute(text("SELECT COUNT(*) FROM best_tasks")).scalar()
            level_count = conn.execute(text("SELECT COUNT(*) FROM best_ranks")).scalar()
    except Exception as e:
        print(f"⚠️ 数据库连接失败，描述简化: {e}")
        task_count = qualified_count = level_count = "N/A"

    # ✅ 显示完整 notes 调试内容
    notes = f"""📊 上传时间：{now_str}
🧮 任务总数：{task_count}
🎯 命中任务：{qualified_count}
🏅 高等级任务：{level_count}"""
    print("📋 生成上传说明 notes 内容如下：")
    print("=" * 40)
    print(notes.strip())
    print("=" * 40)

    # ✅ 写入 notes 临时文件
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8', suffix='.txt') as f:
        f.write(notes)
        f.flush()
        notes_path = f.name
        print("📋 notes 写入临时文件：", notes_path)

    # ✅ 4. 创建 GitHub Release（如已存在则更新描述）
    check_cmd = (
        f"gh release view p5_{playtype_en} "
        f"--repo suwei8/LottoAI3_HitMatrix_date"
    )

    check_result = subprocess.run(
        check_cmd,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if check_result.returncode == 0:
        print(f"ℹ️ Release p5_{playtype_en} 已存在 ➜ 更新描述信息")
        update_cmd = (
            f"gh release edit p5_{playtype_en} "
            f"--repo suwei8/LottoAI3_HitMatrix_date "
            f"--notes-file \"{notes_path}\""
        )
        run_command(update_cmd, use_shell=True)
    else:
        create_cmd = (
            f"gh release create p5_{playtype_en} "
            f"--repo suwei8/LottoAI3_HitMatrix_date "
            f"--title 'p5_{playtype_en}' "
            f"--notes-file \"{notes_path}\""
        )
        run_command(create_cmd, use_shell=True)

    # ✅ 5. 覆盖上传文件
    upload_cmd = (
        f"gh release upload p5_{playtype_en} {zip_name} "
        f"--clobber --repo suwei8/LottoAI3_HitMatrix_date"
    )
    run_command(upload_cmd, use_shell=True)
