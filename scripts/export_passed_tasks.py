# ✅ export_passed_tasks.py - 导出 analyzed_tasks_passed_xx 表并上传 Release（SQL 文件）
import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv
import pyminizip

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log

load_dotenv()

lottery_type = sys.argv[1] if len(sys.argv) > 1 else "3d"
table_name = f"analyzed_tasks_passed_{lottery_type}"

dump_dir = "data"
os.makedirs(dump_dir, exist_ok=True)
dump_file = os.path.join(dump_dir, f"{table_name}.sql")
zip_file = f"{table_name}.sql.zip"
zip_path = os.path.join(dump_dir, zip_file)

# ✅ 数据库连接信息
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD", "123456")
REPO = os.getenv("GITHUB_REPO", "suwei8/LottoAI3_HitMatrix")
TAG = f"analyzed_tasks_passed-{lottery_type}"
TITLE = "analyzed_tasks_passed"

# ✅ 导出 SQL
cmd = [
    "mysqldump",
    f"-h{MYSQL_HOST}",
    f"-P{MYSQL_PORT}",
    f"-u{MYSQL_USER}",
    f"-p{MYSQL_PASSWORD}",
    MYSQL_DATABASE,
    table_name
]
print(f"📤 正在导出数据库表: {table_name} ➜ {dump_file}")
with open(dump_file, "wb") as f:
    subprocess.run(cmd, stdout=f, check=True)

# ✅ 使用 pyminizip 加密压缩
print(f"🔐 开始加密压缩: {zip_path}")
pyminizip.compress(dump_file, None, zip_path, BACKUP_PASSWORD, 5)
print(f"✅ 压缩成功: {zip_path}")

# ✅ 删除旧 Release（静默）
subprocess.run(["gh", "release", "delete", TAG, "--yes"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ✅ 上传 Release
subprocess.run([
    "gh", "release", "create", TAG,
    "--repo", REPO,
    "--title", TITLE,
    "--notes", f"🎯 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n来源表: {table_name}",
    zip_path
], check=True)

print(f"🚀 Release 上传成功 ➜ {REPO}/releases/tag/{TAG}")
