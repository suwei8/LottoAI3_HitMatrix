# scripts/analyze_best_tasks.py
import os, sys, time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import yaml
from datetime import datetime
from sqlalchemy import text
from collections import defaultdict
from utils.db import get_engine, get_lottery_name, get_table_name
from utils.config_loader import load_base_config
from utils.expert_hit_analysis import run_hit_analysis_batch, analyze_expert_hits, get_position_name_map
import re

def analyze_best_tasks_for_issues(issues, lottery_name, best_tasks_table, filter_position, config):
    engine = get_engine()
    results = []

    ENABLE_HIT_CHECK = config.get("ENABLE_HIT_CHECK", True)
    ENABLE_TRACK_OPEN_RANK = config.get("ENABLE_TRACK_OPEN_RANK", True)
    CHECK_MODE = config.get("CHECK_MODE", "dingwei")
    ALL_MODE_LIMIT = config.get("ALL_MODE_LIMIT")

    with engine.begin() as conn:
        sql = f"SELECT * FROM {best_tasks_table} WHERE hit_rate >= 0.9"
        if filter_position is not None:
            sql += f" AND position = {filter_position}"
        rows = list(conn.execute(text(sql)).mappings())
        print(f"\n🎯 共 {len(rows)} 个任务命中率为 0.9", end="")
        if filter_position is not None:
            print(f"，分位={filter_position}", end="")
        print("，将逐个分析...")

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

            print("\n🧩 当前任务配置：")
            print(f"  ➤ ID={task_id} | 分位={position} | 玩法={playtype}")
            print(f"  ➤ lookback_n={lookback_n} | lookback_offset={lookback_offset}")
            print(f"  ➤ hit_rank_list={hit_rank_list}")
            print(f"  ➤ enable={enable_json}")

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
                result = run_hit_analysis_batch(
                    engine=engine,
                    lottery_name=lottery_name,
                    query_issues=issues,
                    all_mode_limit=ALL_MODE_LIMIT,
                    enable_hit_check=ENABLE_HIT_CHECK,
                    enable_track_open_rank=ENABLE_TRACK_OPEN_RANK,
                    dingwei_sha_pos=position,
                    check_mode=CHECK_MODE,
                    analysis_kwargs=analysis_kwargs
                )

                # ⬅️ 在这里加这段完整逻辑
                # ✅ 正确提取命中率
                full_hit_rate = 1.0
                if isinstance(result, dict):
                    try:
                        total = result.get("total_issues", 0)
                        hit = result.get("hit_count", 0)
                        if total > 0:
                            full_hit_rate = round(hit / total, 4)
                            print(f"✅ 提取命中率成功（来自 dict）: {hit} / {total} = {full_hit_rate}")
                        else:
                            print(f"⚠️ total_issues 为 0，跳过任务 {task_id}")
                            continue
                    except Exception as e:
                        print(f"❌ 提取命中率失败: {e}")
                else:
                    result_str = str(result)
                    match = re.search(r"命中率[：:]\s*\d+\s*/\s*\d+\s*=\s*(\d+\.\d+)", result_str)
                    if match:
                        full_hit_rate = float(match.group(1))
                        print(f"✅ 提取命中率成功（来自字符串）: {full_hit_rate}")
                    else:
                        print(f"❌ 未提取到命中率 ➜ 原始 result:\n{result_str}")

                if full_hit_rate < 0.7:
                    print(f"⚠️ 全期命中率 {full_hit_rate:.2f} 低于阈值 0.8，任务 {task_id} 将被删除")
                    delete_sql = f"DELETE FROM {best_tasks_table} WHERE id = {task_id}"
                    conn.execute(text(delete_sql))
                    print("✅ 已从数据库中删除该任务")
                    continue

                recommend = result.get(enable_type, []) if isinstance(result, dict) else []

            except Exception as e:
                recommend = f"❌ 异常: {e}"
            results.append({
                "id": task_id,
                "playtype": playtype,
                "position": position,
                "recommend": recommend,
                "hit_rate": hit_rate
            })

        invalid_ids = [r["id"] for r in results if r["recommend"] is None]
        if invalid_ids:
            print(f"\n🧹 共有 {len(invalid_ids)} 个推荐结果为 None 的任务将被删除：{invalid_ids}")
            delete_sql = f"DELETE FROM {best_tasks_table} WHERE id IN ({','.join(map(str, invalid_ids))})"
            conn.execute(text(delete_sql))
            print(f"✅ 已从数据库中删除 {len(invalid_ids)} 个无效任务。")

    return results


if __name__ == "__main__":
    lottery_type = sys.argv[1] if len(sys.argv) > 1 else "p5"
    filter_position = int(sys.argv[2]) if len(sys.argv) > 2 else None
    lottery_name = get_lottery_name(lottery_type)

    config_path = os.path.join("config", f"{lottery_type}_base.yaml")
    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
        config = raw_config.get("DEFAULTS", raw_config)

    expert_table = get_table_name(lottery_name, "expert_predictions")
    best_tasks_table = get_table_name(lottery_name, "best_tasks")

    engine = get_engine()
    with engine.connect() as conn:
        if str(config.get("QUERY_ISSUES", "")).lower() == "all":
            issues = [r[0] for r in conn.execute(text(
                f"SELECT DISTINCT issue_name FROM {expert_table} ORDER BY issue_name"
            )).fetchall()]
        else:
            issues = config.get("QUERY_ISSUES")
            if isinstance(issues, str):
                issues = [issues]

    start_time = time.time()

    results = analyze_best_tasks_for_issues(
        issues=issues,
        lottery_name=lottery_name,
        best_tasks_table=best_tasks_table,
        filter_position=filter_position,
        config=config
    )

    for r in results:
        print(f"🎯 ID={r['id']} ➜ 分位={r['position']} ➜ 玩法={r['playtype']} ➜ 命中率：{r['hit_rate']:.2f} ➜ 推荐结果：{r['recommend']}")

    summary = defaultdict(list)
    position_name_map = get_position_name_map(lottery_name)
    for r in results:
        pos = r["position"]
        if isinstance(r["recommend"], list):
            summary[pos].extend(r["recommend"])

    run_number = os.getenv("GITHUB_RUN_NUMBER", "本地调试")
    summary_lines = [
        f"📊{lottery_name}-{','.join(issues)}期杀号汇总",
        f"【Actions 运行编号: #{run_number}】"
    ]
    for pos, nums in sorted(summary.items()):
        unique_sorted = sorted(set(nums))
        label = position_name_map.get(pos, f"分位{pos}")
        summary_lines.append(f"{label}（{len(unique_sorted)}）：{','.join(str(n) for n in unique_sorted)}")

    end_time = time.time()
    duration = int(end_time - start_time)
    summary_lines.append(f"📌 耗时：{duration // 60}分{duration % 60}秒")
    summary_lines.append("🕒 分析结束时间：")
    summary_lines.append(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    summary_text = "\n".join(summary_lines)
    print("\n📨 企业微信发送内容：\n" + summary_text)

    # try:
    #     import requests
    #     response = requests.post(
    #         os.getenv("WECHAT_API_URL"),
    #         headers={
    #             "Content-Type": "application/json",
    #             "x-api-key": os.getenv("WECHAT_API_KEY")
    #         },
    #         json={"content": summary_text}
    #     )
    #     print(f"✅ 企业微信已发送，状态码: {response.status_code}")
    #     print(f"返回内容：{response.text}")
    # except Exception as e:
    #     print(f"❌ 企业微信发送失败: {e}")