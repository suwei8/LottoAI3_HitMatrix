#!/bin/bash
# ✅ 本地执行达标组合分析任务（支持 p5 / 3d / all）

# 脚本路径安全设定
cd "$(dirname "$0")/.."

# 自动加载 .env 环境变量
if [ -f .env ]; then
  echo "📦 加载本地环境变量 .env ..."
  set -a
  source .env
  set +a
else
  echo "❌ 未找到 .env 文件，终止"
  exit 1
fi

LOTTERY_TYPE=$1

if [[ "$LOTTERY_TYPE" != "3d" && "$LOTTERY_TYPE" != "p5" && "$LOTTERY_TYPE" != "all" ]]; then
  echo "❌ 参数错误：请输入 3d / p5 / all"
  exit 1
fi

echo "🎯 当前分析任务类型: $LOTTERY_TYPE"
echo "📅 开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
START_TIME=$(date +%s)

run_analysis() {
  local lottery=$1
  local max_pos=$2
  echo "====== 🔍 分析 $lottery ======"
  for pos in $(seq 0 $max_pos); do
    echo "➡️ 分析 $lottery - 分位 $pos"
    python3 scripts/analyze_best_tasks.py $lottery $pos
  done
}

if [[ "$LOTTERY_TYPE" == "3d" ]]; then
  run_analysis 3d 2
elif [[ "$LOTTERY_TYPE" == "p5" ]]; then
  run_analysis p5 4
else
  run_analysis 3d 2
  run_analysis p5 4
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "✅ 分析完成，总耗时 ${DURATION} 秒（约 $((DURATION / 60)) 分钟）"
echo "📅 结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
