# ✅ run_from_best_tasks.py - 支持分析结果写入 passed / failed 表，并跳过已分析组合，并在达标后立即上传 Release
import os
import sys
import json
import builtins
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log, save_log_file_if_needed, init_log_capture
from utils.db import get_engine, get_table_name, get_lottery_name
from utils.expert_hit_analysis import run_hit_analysis_batch

# ✅ 初始化日志
if "__print_original__" not in builtins.__dict__:
    builtins.__dict__["__print_original__"] = print
init_log_capture(script_name_hint=os.path.basename(__file__))
print = log

# ✅ 加载配置
load_dotenv()
lottery_type = os.getenv("LOTTERY_TYPE", "3d")
lottery_name = get_lottery_name(lottery_type)
best_tasks_table = get_table_name(lottery_name, "best_tasks")
filter_position = os.getenv("FILTER_POSITION")
filter_position = int(filter_position) if filter_position is not None else None
lookback_n = int(os.getenv("LOOKBACK_N", "30"))
check_mode = os.getenv("CHECK_MODE", "dingwei")
engine = get_engine()

# ✅ 获取最新期号列表
with engine.begin() as trans:
    result = trans.execute(text(f"""
        SELECT DISTINCT issue_name FROM {get_table_name(lottery_name, 'expert_predictions')}
        ORDER BY issue_name DESC LIMIT {lookback_n}
    """))
    query_issues = [row[0] for row in result.fetchall()][::-1]
print(f"✅ QUERY_ISSUES: {query_issues}")

# ✅ 获取已分析 origin_id（passed + failed）
with engine.begin() as conn:
    analyzed_ids = set(conn.execute(text(f"""
        SELECT origin_id FROM analyzed_tasks_passed_{lottery_type}
        UNION
        SELECT origin_id FROM analyzed_tasks_failed_{lottery_type}
    """)).scalars().all())

# ✅ 加载待分析组合任务
with engine.begin() as trans:
    if filter_position is not None:
        sql = text(f"SELECT * FROM {best_tasks_table} WHERE hit_rate >= 0.9 AND position = {filter_position}")
    else:
        sql = text(f"SELECT * FROM {best_tasks_table} WHERE hit_rate >= 0.9")
    raw_tasks = list(trans.execute(sql).mappings())
    tasks = [t for t in raw_tasks if t["id"] not in analyzed_ids]

print(f"📦 原始任务: {len(raw_tasks)} ➜ 待分析（未处理）: {len(tasks)}")

# ✅ 执行分析
hit_count = 0
miss_count = 0
skip_count = 0

for task in tasks:
    task_id = task['id']
    playtype = task["playtype"]
    position = task["position"]
    hit_rank_list = json.loads(task["hit_rank_list"])
    enable = json.loads(task["enable"])
    enable_type = list(enable.keys())[0]
    enable_value = enable[enable_type]
    lookback_n = task["lookback_n"]
    lookback_offset = task["lookback_offset"]

    analysis_kwargs = {
        "query_playtype_name": playtype,
        "analyze_playtype_name": playtype,
        "mode": "rank",
        "hit_rank_list": hit_rank_list,
        "lookback_n": lookback_n,
        "lookback_start_offset": lookback_offset,
        f"enable_{enable_type}": enable_value,
    }

    print(f"\n🎯 当前组合: ID={task_id} ➜ 玩法={playtype} ➜ 分位={position} ➜ 命中率={task['hit_rate']}")

    try:
        result = run_hit_analysis_batch(
            engine=engine,
            lottery_name=lottery_name,
            query_issues=query_issues,
            all_mode_limit=None,
            enable_hit_check=True,
            enable_track_open_rank=True,
            dingwei_sha_pos=position,
            check_mode=check_mode,
            analysis_kwargs=analysis_kwargs
        )

        if isinstance(result, dict):
            cur_hit = result.get("hit_count", 0)
            cur_miss = result.get("miss_count", 0)
            cur_skip = result.get("skip_count", 0)
            total = cur_hit + cur_miss
            hit_rate_actual = round(cur_hit / total, 4) if total > 0 else 0.0
            hit_count += cur_hit
            miss_count += cur_miss
            skip_count += cur_skip
        else:
            hit_rate_actual = 0.0
            total = 0

        # ✅ 写入结果表
        target_table = f"analyzed_tasks_passed_{lottery_type}" if hit_rate_actual >= 0.9 else f"analyzed_tasks_failed_{lottery_type}"
        with engine.begin() as trans:
            trans.execute(text(f"""
                INSERT IGNORE INTO {target_table}
                (origin_id, lottery_type, playtype, position, lookback_n, hit_rank_list, enable, analyzed_hit_rate, total_issues, created_at)
                VALUES (:origin_id, :lottery_type, :playtype, :position, :lookback_n, :hit_rank_list, :enable, :analyzed_hit_rate, :total_issues, NOW())
            """), dict(
                origin_id=task_id,
                lottery_type=lottery_type,
                playtype=playtype,
                position=position,
                lookback_n=lookback_n,
                hit_rank_list=json.dumps(hit_rank_list, ensure_ascii=False),
                enable=json.dumps(enable, ensure_ascii=False),
                analyzed_hit_rate=hit_rate_actual,
                total_issues=total
            ))

        # ✅ 如果是达标，立即执行上传
        if hit_rate_actual >= 0.9:
            print(f"📤 达标任务 ID={task_id}，开始上传 Release")
            subprocess.run([sys.executable, "scripts/export_passed_tasks.py", lottery_type])
            time.sleep(1)

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        skip_count += 1
        continue

# ✅ 汇总统计
print("\n==============================")
print(f"📉 共分析组合: {len(tasks)}，命中：{hit_count}，未命中：{miss_count}，跳过：{skip_count}")
if hit_count + miss_count > 0:
    hit_rate = hit_count / (hit_count + miss_count)
    print(f"✅ 命中率：{hit_count} / {hit_count + miss_count} = {hit_rate:.4f}")
save_log_file_if_needed(True)
