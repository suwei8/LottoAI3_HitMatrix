#!/bin/bash
set -e

# ✅ 加载 .env 配置
export $(grep -v '^#' .env | xargs)

# ✅ 启动 MySQL 容器（如已启动可跳过）
docker run -d \
  --name mysql-service-local \
  -e MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD \
  -e MYSQL_DATABASE=$MYSQL_DATABASE \
  -p 3306:3306 \
  --health-cmd="mysqladmin ping -h 127.0.0.1 --silent" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=30 \
  mysql:8.0.36

# ✅ 等待容器健康
for i in {1..30}; do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' mysql-service-local 2>/dev/null || echo "notfound")
  if [[ "$STATUS" == "healthy" ]]; then
    echo "✅ MySQL 容器已就绪"
    break
  fi
  echo "⏳ 等待中 ($i)..."
  sleep 2
done

# ✅ 下载并导入 best_tasks_ok 表
mkdir -p data
curl -L -o data/best_tasks_ok.zip \
  https://github.com/suwei8/LottoAI3_HitMatrix/releases/download/ok/best_tasks_ok.sql.zip
unzip -P "$BACKUP_PASSWORD" -d data/ data/best_tasks_ok.zip
pv data/best_tasks_ok.sql | mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE

# ✅ 下载最近30期数据（以 p5 为例，支持 all / 3d 切换）
LOTTERY_TYPE=${1:-p5}

restore_data() {
  local lottery=$1
  if [ "$lottery" = "3d" ]; then
    REPO="LottoAI3_HitMatrix_date_3d"
  else
    REPO="LottoAI3_HitMatrix_date"
  fi

  curl -L -o data/lotto_${lottery}_backup.zip \
    https://github.com/suwei8/${REPO}/releases/download/backup-${lottery}/lotto_${lottery}_backup.zip

  unzip -P "$BACKUP_PASSWORD" -d data/ data/lotto_${lottery}_backup.zip
  gunzip -c data/lotto_${lottery}.sql.gz | \
    pv -s $(gzip -l data/lotto_${lottery}.sql.gz | awk 'NR==2 {print $2}') | \
    mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE
}

if [[ "$LOTTERY_TYPE" == "all" ]]; then
  restore_data 3d
  restore_data p5
else
  restore_data "$LOTTERY_TYPE"
fi

# ✅ 安装依赖（确保虚拟环境或已激活环境）
pip install -r requirements.txt

# ✅ 执行分析（根据传入 lottery_type）
run_analysis() {
  local lottery=$1
  local max_pos=$2
  for pos in $(seq 0 $max_pos); do
    echo "📊 分析 $lottery ➜ 分位 $pos"
    python scripts/analyze_best_tasks.py $lottery $pos
  done
}

if [[ "$LOTTERY_TYPE" == "3d" ]]; then
  run_analysis 3d 2
elif [[ "$LOTTERY_TYPE" == "p5" ]]; then
  run_analysis p5 4
elif [[ "$LOTTERY_TYPE" == "all" ]]; then
  run_analysis 3d 2
  run_analysis p5 4
else
  echo "❌ 无效彩种类型: $LOTTERY_TYPE"
  exit 1
fi

# ✅ 导出结果
mkdir -p best_tasks_export
mysqldump -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD \
  $MYSQL_DATABASE best_tasks_3d best_tasks_p5 > best_tasks_export/best_tasks_ok.sql
cd best_tasks_export
zip -P "$BACKUP_PASSWORD" best_tasks_ok.sql.zip best_tasks_ok.sql
cd ..

# ✅ 上传 GitHub Releases（需 gh CLI 已认证）
gh release upload ok best_tasks_export/best_tasks_ok.sql.zip --clobber

