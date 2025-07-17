# scripts/init_tables.py

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tempfile
import subprocess
import requests
import zipfile
import time
from dotenv import load_dotenv
from utils.db import get_engine
from sqlalchemy import text, inspect

if os.getenv("GITHUB_ACTIONS") != "true":
    load_dotenv(override=False)

# ✅ 基础配置
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ✅ 支持多种彩票
BACKUP_LINKS = {
    "p5": {
        "init": [
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/tasks_p5/tasks_p5.sql.zip"
        ],
        "tasks": [
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_sha3/p5_tasks_gewei_sha3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_sha1/p5_tasks_gewei_sha1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_ding5/p5_tasks_gewei_ding5.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_ding3/p5_tasks_baiwei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_ding1/p5_tasks_baiwei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_sha3/p5_tasks_shiwei_sha3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_sha1/p5_tasks_shiwei_sha1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_ding5/p5_tasks_shiwei_ding5.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_ding3/p5_tasks_qianwei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_ding1/p5_tasks_qianwei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_sha3/p5_tasks_wanwei_sha3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_sha1/p5_tasks_wanwei_sha1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_sha3/p5_tasks_baiwei_sha3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_sha1/p5_tasks_baiwei_sha1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_ding5/p5_tasks_baiwei_ding5.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_ding3/p5_tasks_gewei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_ding1/p5_tasks_gewei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_sha3/p5_tasks_qianwei_sha3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_sha1/p5_tasks_qianwei_sha1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_ding5/p5_tasks_qianwei_ding5.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_ding3/p5_tasks_shiwei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_ding1/p5_tasks_shiwei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_ding5/p5_tasks_wanwei_ding5.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_ding3/p5_tasks_wanwei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_ding1/p5_tasks_wanwei_ding1.sql.zip"
        ]
    },
    "3d": {
        "init": [
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/v0.1/tasks_3d.sql.zip"
        ],
        "tasks": [
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_shuangdan_2/3d_tasks_shuangdan_2.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_liuma_zuxuan/3d_tasks_liuma_zuxuan.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_sha2/3d_tasks_sha2.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_shiwei_ding3/3d_tasks_shiwei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_baiwei_ding1/3d_tasks_baiwei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_gewei_ding1/3d_tasks_gewei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_3x3x3_shi/3d_tasks_ding_3x3x3_shi.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_4x4x4_bai/3d_tasks_ding_4x4x4_bai.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_4x4x4_ge/3d_tasks_ding_4x4x4_ge.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_5x5x5_shi/3d_tasks_ding_5x5x5_shi.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_5x5x5_ge/3d_tasks_ding_5x5x5_ge.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_danguan_1/3d_tasks_danguan_1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_sandan_3/3d_tasks_sandan_3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_wuma_zuxuan/3d_tasks_wuma_zuxuan.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_qima_zuxuan/3d_tasks_qima_zuxuan.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_sha1/3d_tasks_sha1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_baiwei_ding3/3d_tasks_baiwei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_gewei_ding3/3d_tasks_gewei_ding3.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_shiwei_ding1/3d_tasks_shiwei_ding1.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_3x3x3_bai/3d_tasks_ding_3x3x3_bai.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_3x3x3_ge/3d_tasks_ding_3x3x3_ge.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_4x4x4_shi/3d_tasks_ding_4x4x4_shi.sql.zip",
            "https://github.com/suwei8/LottoAI3_HitMatrix_date_3d/releases/download/3d_ding_5x5x5_bai/3d_tasks_ding_5x5x5_bai.sql.zip"
        ]
    }
}

def download_and_unzip_to(path: str, url: str, password: str) -> str:
    filename = url.split("/")[-1].replace(".sql.zip", "").split("_tasks_")[-1] + ".sql"
    dest_sql_path = os.path.join(path, filename)

    print(f"\n📅 下载并解压: {url} → {dest_sql_path}")
    r = requests.get(url)
    zip_path = os.path.join(path, "tmp.zip")
    with open(zip_path, "wb") as f:
        f.write(r.content)

    with zipfile.ZipFile(zip_path) as zf:
        zf.setpassword(password.encode())
        for name in zf.namelist():
            if name.endswith(".sql"):
                zf.extract(name, path)
                os.rename(os.path.join(path, name), dest_sql_path)
                return dest_sql_path
    raise RuntimeError("❌ 解压失败，未找到 SQL 文件")

def is_table_missing_or_empty(engine, table_name):
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        print(f"❌ 表不存在: {table_name}")
        return True
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        print(f"📊 {table_name} 记录数: {count}")
        return count == 0

def import_sql_file(path: str):
    print(f"\n📄 导入 SQL: {path}")
    cmd = ["mysql", f"-h{MYSQL_HOST}", f"-P{MYSQL_PORT}", f"-u{MYSQL_USER}", f"-p{MYSQL_PASSWORD}", MYSQL_DATABASE]
    with open(path, "rb") as f:
        subprocess.run(cmd, stdin=f, check=True)
    print("✅ 导入成功")

def main():
    if len(sys.argv) < 2:
        print("❌ 缺少参数：请指定 lottery_type，例如：python scripts/init_tables.py p5")
        sys.exit(1)

    lottery_type = sys.argv[1]
    table_suffix = f"_{lottery_type}"

    tasks_table = f"tasks{table_suffix}"
    best_tasks_table = f"best_tasks{table_suffix}"
    best_ranks_table = f"best_ranks{table_suffix}"

    if lottery_type not in BACKUP_LINKS:
        print(f"❌ 未配置的彩种类型: {lottery_type}，请检查 BACKUP_LINKS 中是否定义了 '{lottery_type}'")
        sys.exit(1)

    init_links = BACKUP_LINKS[lottery_type]["init"]
    task_links = BACKUP_LINKS[lottery_type]["tasks"]


    engine = get_engine()
    if not any(is_table_missing_or_empty(engine, t) for t in [tasks_table, best_tasks_table, best_ranks_table]):
        print(f"✅ 所有表存在且不为空，跳过初始化: {lottery_type}")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        for url in init_links:
            path = download_and_unzip_to(tmpdir, url, BACKUP_PASSWORD)
            import_sql_file(path)

    for idx, url in enumerate(task_links):
        print(f"\n⏳ 下载第 {idx + 1}/{len(task_links)} 个任务 SQL，延时 1 秒...")
        download_and_unzip_to(DATA_DIR, url, BACKUP_PASSWORD)
        time.sleep(1)

    print(f"\n🧌 执行 SQL 合并： merge_sqls_with_incremental_id.py {lottery_type}")
    subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "scripts", "merge_sqls_with_incremental_id.py"), lottery_type], check=True)

    merged_path = os.path.join(DATA_DIR, f"merged_tasks_{lottery_type}.sql")
    import_sql_file(merged_path)
    print(f"✅ {lottery_type} 初始化流程全部完成")

if __name__ == "__main__":
    main()
