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

BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BACKUP_LINKS = {
    "init_p5": [
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/tasks_p5/tasks_p5.sql.zip"
    ],
    "tasks_p5": [
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_sha3/p5_hitmatrix_gewei_sha3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_sha1/p5_hitmatrix_gewei_sha1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_ding5/p5_hitmatrix_gewei_ding5.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_ding3/p5_hitmatrix_baiwei_ding3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_ding1/p5_hitmatrix_baiwei_ding1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_sha3/p5_hitmatrix_shiwei_sha3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_sha1/p5_hitmatrix_shiwei_sha1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_ding5/p5_hitmatrix_shiwei_ding5.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_ding3/p5_hitmatrix_qianwei_ding3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_ding1/p5_hitmatrix_qianwei_ding1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_sha3/p5_hitmatrix_wanwei_sha3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_sha1/p5_hitmatrix_wanwei_sha1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_sha3/p5_hitmatrix_baiwei_sha3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_sha1/p5_hitmatrix_baiwei_sha1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_baiwei_ding5/p5_hitmatrix_baiwei_ding5.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_ding3/p5_hitmatrix_gewei_ding3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_gewei_ding1/p5_hitmatrix_gewei_ding1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_sha3/p5_hitmatrix_qianwei_sha3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_sha1/p5_hitmatrix_qianwei_sha1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_qianwei_ding5/p5_hitmatrix_qianwei_ding5.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_ding3/p5_hitmatrix_shiwei_ding3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_shiwei_ding1/p5_hitmatrix_shiwei_ding1.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_ding5/p5_hitmatrix_wanwei_ding5.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_ding3/p5_hitmatrix_wanwei_ding3.sql.zip",
        "https://github.com/suwei8/LottoAI3_HitMatrix_date/releases/download/p5_wanwei_ding1/p5_hitmatrix_wanwei_ding1.sql.zip"
    ]
}

def download_and_unzip_to(path: str, url: str, password: str) -> str:
    filename = url.split("/")[-1].replace(".sql.zip", "").replace("p5_hitmatrix_", "") + ".sql"
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
    engine = get_engine()
    if not any(is_table_missing_or_empty(engine, t) for t in ["tasks_p5", "best_tasks_p5", "best_ranks_p5"]):
        print("✅ 所有表存在且不为空，跳过初始化")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        for url in BACKUP_LINKS["init_p5"]:
            path = download_and_unzip_to(tmpdir, url, BACKUP_PASSWORD)
            import_sql_file(path)

    for idx, url in enumerate(BACKUP_LINKS["tasks_p5"]):
        print(f"\n⏳ 下载第 {idx + 1}/{len(BACKUP_LINKS['tasks_p5'])} 个任务 SQL，延时 1 秒...")
        download_and_unzip_to(DATA_DIR, url, BACKUP_PASSWORD)
        time.sleep(1)

    print("\n🧌 执行 SQL 合并： merge_sqls_with_incremental_id.py")
    subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, "scripts", "merge_sqls_with_incremental_id.py")], check=True)

    merged_path = os.path.join(DATA_DIR, "merged_tasks_p5.sql")
    import_sql_file(merged_path)
    print("✅ 初始化流程全部完成")
if __name__ == "__main__":
    main()
