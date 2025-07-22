import os
import subprocess

# === 数据库配置 ===
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "sw63828"
MYSQL_DATABASE = "lotto_ai3_hitmatrix"

# === 获取当前目录下所有 .sql 文件 ===
sql_files = [f for f in os.listdir('.') if f.endswith('.sql')]

if not sql_files:
    print("⚠️ 当前目录下未找到任何 .sql 文件")
    exit(1)

# === 恢复每个 SQL 文件 ===
for sql_file in sql_files:
    print(f"📄 正在导入：{sql_file}")
    cmd = [
        "mysql",
        f"-h{MYSQL_HOST}",
        f"-P{MYSQL_PORT}",
        f"-u{MYSQL_USER}",
        f"-p{MYSQL_PASSWORD}",
        MYSQL_DATABASE
    ]

    with open(sql_file, 'rb') as f:
        result = subprocess.run(cmd, stdin=f)

    if result.returncode == 0:
        print(f"✅ 成功导入：{sql_file}")
    else:
        print(f"❌ 导入失败：{sql_file}")

print("🎉 所有 SQL 文件处理完成。")
