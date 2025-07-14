# scripts/analyze_best_tasks.py
"""
📌 脚本名称：analyze_best_tasks.py
📂 所属模块：scripts/

🎯 脚本功能简介：
本脚本用于批量执行 best_tasks 表中达标组合配置，对指定期号的排列5推荐数据进行分析与验证。

核心功能包括：
- ✅ 自动读取 best_tasks 表中所有组合策略参数；
- ✅ 调用 run_hit_analysis_batch 执行推荐生成 + 命中判断 + 排名统计；
- ✅ 自动打印任务参数（ID、玩法、lookback、命中率等）与推荐结果；
- ✅ 输出格式统一，支持接入 GitHub Actions 自动化执行或本地批量验证。

🧩 示例用途：
- 精准验证高命中组合对指定期号的表现；
- 快速批量对比不同组合效果；
- 生成推荐数字并追踪命中表现，供部署前评估参考。

"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from sqlalchemy import text
from utils.db import get_engine
from utils.expert_hit_analysis import run_hit_analysis_batch, analyze_expert_hits
import yaml

# ✅ 控制参数
ENABLE_HIT_CHECK = True
ENABLE_TRACK_OPEN_RANK = True
CHECK_MODE = "dingwei"
LOG_SAVE_MODE = False

# ✅ 获取项目根目录（脚本所在目录的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE_DIR, "config", "p5_base.yaml")

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
LOTTERY_NAME = config.get("LOTTERY_NAME", "排列5")


def analyze_best_tasks_for_issue(issue: str, lottery: str = "排列5"):
    engine = get_engine()

    with engine.begin() as conn:
        results = []

        rows = conn.execute(text("SELECT * FROM best_tasks")).mappings()

        for row in rows:
            task_id = row["id"]
            position = row["position"]
            playtype = row["playtype"]
            lookback_n = row["lookback_n"]
            lookback_offset = row["lookback_offset"]
            hit_rank_list = json.loads(row["hit_rank_list"])
            enable_json = json.loads(row["enable"])
            skip_json = json.loads(row["skip_if_few"]) if row["skip_if_few"] else {}
            tie_mode_json = json.loads(row["resolve_tie_mode"]) if row["resolve_tie_mode"] else {}
            reverse_json = json.loads(row["reverse_on_tie"]) if row["reverse_on_tie"] else {}
            hit_rate = row["hit_rate"]

            enable_type = list(enable_json.keys())[0]
            enable_value = enable_json[enable_type]

            # 🧩 打印当前任务配置
            print("🧩 当前任务配置：")
            print(f"  ➤ ID={task_id} | 分位={position} | 玩法={playtype}")
            print(f"  ➤ lookback_n={lookback_n} | lookback_offset={lookback_offset}")
            print(f"  ➤ hit_rank_list={hit_rank_list}")
            print(f"  ➤ enable={enable_json}")
            # 构造分析参数
            analysis_kwargs = {
                "query_playtype_name": playtype,
                "analyze_playtype_name": playtype,
                "mode": "rank",
                "hit_rank_list": hit_rank_list,
                "lookback_n": lookback_n,
                "lookback_start_offset": lookback_offset,
                f"enable_{enable_type}": enable_value,
                f"skip_if_few_{enable_type}": skip_json.get(enable_type, True),
                f"resolve_tie_mode_{enable_type}": tie_mode_json.get(enable_type, "False"),
                f"reverse_on_tie_{enable_type}": reverse_json.get(enable_type, False),
            }

            try:
                # ✅ 执行推荐分析 + 命中判断
                run_hit_analysis_batch(
                    engine=engine,
                    lottery_name=lottery,
                    query_issues=[issue],
                    all_mode_limit=None,
                    enable_hit_check=ENABLE_HIT_CHECK,
                    enable_track_open_rank=ENABLE_TRACK_OPEN_RANK,
                    dingwei_sha_pos=position,
                    check_mode=CHECK_MODE,
                    analysis_kwargs=analysis_kwargs
                )

                # ✅ 获取推荐结果
                result = analyze_expert_hits(
                    engine=engine,
                    lottery_name=lottery,
                    query_issue=issue,
                    dingwei_sha_pos=position,
                    **analysis_kwargs
                )
                recommend = result.get(enable_type, [])

            except Exception as e:
                recommend = f"❌ 异常: {e}"

            results.append({
                "id": task_id,
                "playtype": playtype,
                "position": position,
                "recommend": recommend,
                "hit_rate": hit_rate  # ✅ 确保异常时也有命中率字段
            })

    return results

if __name__ == "__main__":
    # 🔹 获取最新期号
    engine = get_engine()
    with engine.connect() as conn:
        latest_issue = conn.execute(text(
            "SELECT MAX(issue_name) FROM lottery_results_p5"
        )).scalar()
    issue = latest_issue

    # 🔹 执行分析
    results = analyze_best_tasks_for_issue(issue, lottery=LOTTERY_NAME)
    for r in results:
        print(f"🎯 ID={r['id']} ➜ 分位={r['position']} ➜ 玩法={r['playtype']} ➜ 命中率：{r['hit_rate']:.2f} ➜ 推荐结果：{r['recommend']}")

    from collections import defaultdict
    position_name_map = {0: "万位", 1: "千位", 2: "百位", 3: "十位", 4: "个位"}
    summary = defaultdict(list)
    for r in results:
        pos = r["position"]
        if isinstance(r["recommend"], list):
            summary[pos].extend(r["recommend"])

    # 🔹 构造消息文本
    summary_lines = [f"📊{LOTTERY_NAME}-{issue}期杀号汇总"]
    for pos, nums in sorted(summary.items()):
        unique_sorted = sorted(set(nums))
        label = position_name_map.get(pos, f"分位{pos}")
        summary_lines.append(f"{label}：{','.join(str(n) for n in unique_sorted)}")

    summary_text = "\n".join(summary_lines)
    print("\n📨 企业微信发送内容：\n" + summary_text)

    # 🔹 企业微信推送
    try:
        import requests
        response = requests.post(
            os.getenv("WECHAT_API_URL"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("WECHAT_API_KEY")
            },
            json={"content": summary_text}
        )
        print(f"✅ 企业微信已发送，状态码: {response.status_code}")
        print(f"返回内容：{response.text}")
    except Exception as e:
        print(f"❌ 企业微信发送失败: {e}")
