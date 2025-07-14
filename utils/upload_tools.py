import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
import shlex
import pyminizip
import yaml
import time
from sqlalchemy import text
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.db import (
    get_engine,
    get_tasks_table,
    get_best_tasks_table,
    get_best_ranks_table,
)
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
        print("命令输出：", result.stdout)
        sys.exit(result.returncode)
    return result


def load_config_from_yaml(lottery_type: str):
    config_path = f"config/{lottery_type}_base.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"未找到配置文件: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return cfg


def do_final_dump_and_upload(playtype_en: str, lottery_type: str = "3d"):

    # === 读取配置 ===
    config = load_config_from_yaml(lottery_type)
    GITHUB_OWNER = config["GITHUB_OWNER"]
    GITHUB_REPO = config["GITHUB_REPO"]
    RELEASE_TAG = config["RELEASE_TAG"]

    # === 数据库和环境变量 ===
    engine = get_engine()
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")
    GH_TOKEN = os.getenv("GH_TOKEN")

    os.environ["GH_TOKEN"] = GH_TOKEN
    os.environ["GITHUB_TOKEN"] = GH_TOKEN

    tag = f"{RELEASE_TAG}_{playtype_en}"
    zip_name = f"{lottery_type}_hitmatrix_{playtype_en}.sql.zip"

    # === Step1: 导出 SQL ===

    # === 动态获取任务相关表名 ===
    tasks_table = get_tasks_table(config.get("LOTTERY_NAME", "福彩3D"))
    best_tasks_table = get_best_tasks_table(config.get("LOTTERY_NAME", "福彩3D"))
    best_ranks_table = get_best_ranks_table(config.get("LOTTERY_NAME", "福彩3D"))

    dump_cmd = (
        f"mysqldump -h {MYSQL_HOST} -u{MYSQL_USER} -p\"{MYSQL_PASSWORD}\" "
        f"--skip-triggers --set-gtid-purged=OFF --column-statistics=0 "
        f"--add-drop-table --default-character-set=utf8mb4 "
        f"--single-transaction --quick "
        f"{MYSQL_DATABASE} {tasks_table} {best_tasks_table} {best_ranks_table} > tasks_best.sql"
    )

    run_command(dump_cmd, use_shell=True)
    time.sleep(2)  # ✅ 延时2秒，避免数据库未立即释放或压缩前抢占资源

    # === Step2: 压缩加密 ===
    pyminizip.compress("tasks_best.sql", None, zip_name, BACKUP_PASSWORD, 5)
    print(f"✅ 已压缩 ➜ {zip_name}")

    # === Step3: 删除旧 Release（忽略错误）===
    delete_cmd = (
        f"gh release delete {tag} --yes "
        f"--repo {GITHUB_OWNER}/{GITHUB_REPO} || echo '✅ 旧 release 不存在，跳过删除'"
    )
    run_command(delete_cmd, use_shell=True)

    # === Step4: 创建 Release ===
    with engine.begin() as conn:
        total_tasks = conn.execute(text(f"SELECT COUNT(*) FROM {tasks_table}")).scalar()
        done_tasks = conn.execute(text(f"SELECT COUNT(*) FROM {tasks_table} WHERE status = 'done'")).scalar()
        best_tasks = conn.execute(text(f"SELECT COUNT(*) FROM {best_tasks_table}")).scalar()
        now_str = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        notes = (
            f"📊 上传时间：{now_str} ｜ 🧮 任务总数：{total_tasks} ｜ 🎯 命中任务：{done_tasks} ｜ 🏅 高等级任务：{best_tasks}"
        )

        create_cmd = (
            f"gh release create {tag} "
            f"--repo {GITHUB_OWNER}/{GITHUB_REPO} "
            f"--title {tag} "
            f"--notes \"{notes}\""
        )
        run_command(create_cmd, use_shell=True)

    # === Step5: 上传文件 ===
    upload_cmd = (
        f"gh release upload {tag} {zip_name} "
        f"--clobber --repo {GITHUB_OWNER}/{GITHUB_REPO}"
    )
    run_command(upload_cmd, use_shell=True)
