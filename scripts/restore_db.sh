#!/usr/bin/env bash
# =============================================
# LottoAI3 · 高可读性 · 自动排序 · 带时间戳
# =============================================

set -e

MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PWD="${MYSQL_PWD:-$MYSQL_PASSWORD}"  # 从 Actions env 注入
MYSQL_DB="${MYSQL_DATABASE:-lotto_ai3_hitmatrix}"

echo "=============================="
echo "🎯 Restore DB 启动"
echo "🎯 Host: $MYSQL_HOST"
echo "🎯 Database: $MYSQL_DB"
echo "=============================="

SQL_FILES=$(find data -maxdepth 1 -type f -name "*.sql" | sort)

if [ -z "$SQL_FILES" ]; then
  echo "❌ 没有找到可用 SQL 文件！"
  exit 1
fi

for f in $SQL_FILES; do
  echo "----------------------------------------"
  echo "🚩 开始导入: $f"
  date '+⏳ 开始时间: %Y-%m-%d %H:%M:%S'
  mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" < "$f"
  echo "✅ 已完成导入: $f"
  date '+✅ 完成时间: %Y-%m-%d %H:%M:%S'
done

echo "=============================="
echo "🎉 所有 SQL 已全部导入完成！"
echo "=============================="
