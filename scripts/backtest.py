# scripts/backtest.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime
import json
from sqlalchemy import text
from utils.db import get_engine
from utils.logger import log, save_log_file_if_needed
from utils.expert_hit_analysis import run_hit_analysis_batch

engine = get_engine()

with engine.begin() as conn:
    tasks = list(conn.execute(text("SELECT * FROM tasks WHERE status = 'pending'")).mappings())
    if not tasks:
        log("✅ 没有待执行任务，已退出")
        print("待执行任务: 0")  # ✅ 兼容 run_all.py 检查
        sys.exit(0)

    log(f"🎯 待执行任务: {len(tasks)}")

    for task in tasks:
        position = int(task["position"])
        lookback_n = task["lookback_n"]
        lookback_offset = task["lookback_offset"]
        query_playtype_name = task["query_playtype_name"]
        analyze_playtype_name = task["analyze_playtype_name"]
        hit_rank_list = json.loads(task["hit_rank_list"])
        enable = json.loads(task["enable"])
        skip_if_few = json.loads(task["skip_if_few"])
        resolve_tie_mode = json.loads(task["resolve_tie_mode"])
        reverse_on_tie = json.loads(task["reverse_on_tie"])

        enable_dingwei_sha = enable.get("dingwei_sha")
        skip_if_few_dingwei_sha = skip_if_few.get("dingwei_sha")
        resolve_tie_mode_dingwei_sha = resolve_tie_mode.get("dingwei_sha")
        reverse_on_tie_dingwei_sha = reverse_on_tie.get("dingwei_sha")

        if enable_dingwei_sha and not isinstance(enable_dingwei_sha, list):
            enable_dingwei_sha = [enable_dingwei_sha]

        log(f"🚩 ID={task['id']} ➜ {query_playtype_name} | lookback_n={lookback_n} | HR={hit_rank_list} | enable={enable_dingwei_sha}")

        result = run_hit_analysis_batch(
            engine=engine,
            lottery_name="排列5",
            query_issues=["All"],
            enable_hit_check=True,
            enable_track_open_rank=True,
            dingwei_sha_pos=position,
            check_mode="dingwei",
            analysis_kwargs=dict(
                query_playtype_name=query_playtype_name,
                analyze_playtype_name=analyze_playtype_name,
                mode="rank",
                hit_rank_list=hit_rank_list,
                lookback_n=lookback_n,
                lookback_start_offset=lookback_offset,
                enable_dingwei_sha=enable_dingwei_sha,
                skip_if_few_dingwei_sha=skip_if_few_dingwei_sha,
                resolve_tie_mode_dingwei_sha=resolve_tie_mode_dingwei_sha,
                reverse_on_tie_dingwei_sha=reverse_on_tie_dingwei_sha,
            )
        )

        total_issues = result["total_issues"]
        miss_count = result["miss_count"]
        skip_count = result["skip_count"]

        effective_total = total_issues - skip_count
        hit_count = effective_total - miss_count
        hit_rate = round(hit_count / effective_total, 4) if effective_total > 0 else 0


        log(f"📈 ID={task['id']} ➜ 命中 {hit_count}/{total_issues} ➜ 命中率={hit_rate}")

        conn.execute(text("""
            UPDATE tasks
            SET status='done', total_issues=:total_issues, hit_count=:hit_count,
                skip_count=:skip_count, hit_rate=:hit_rate, updated_at=:updated_at
            WHERE id=:id
        """), dict(
            id=task["id"],
            total_issues=total_issues,
            hit_count=hit_count,
            skip_count=skip_count,
            hit_rate=hit_rate,
            updated_at=datetime.now()
        ))

        if hit_rate >= 0.8:
            conn.execute(text("""
                INSERT IGNORE INTO best_tasks
                (position, playtype, lookback_n, hit_rank_list, enable, skip_if_few,
                 resolve_tie_mode, reverse_on_tie, hit_rate, created_at)
                VALUES (:position, :playtype, :lookback_n, :hit_rank_list, :enable,
                        :skip_if_few, :resolve_tie_mode, :reverse_on_tie, :hit_rate, :created_at)
            """), dict(
                position=position,
                playtype=query_playtype_name,
                lookback_n=lookback_n,
                hit_rank_list=json.dumps(hit_rank_list, ensure_ascii=False),
                enable=json.dumps(enable, ensure_ascii=False),
                skip_if_few=json.dumps(skip_if_few, ensure_ascii=False),
                resolve_tie_mode=json.dumps(resolve_tie_mode, ensure_ascii=False),
                reverse_on_tie=json.dumps(reverse_on_tie, ensure_ascii=False),
                hit_rate=hit_rate,
                created_at=datetime.now()
            ))

        open_rank_counter = result.get("open_rank_counter", {})
        max_rank = result.get("max_rank_length", 0)
        log(f"✅ 调试: open_rank_counter={open_rank_counter} max_rank={max_rank}")
        all_possible = list(range(1, max_rank + 1))
        zero_ranks = [r for r in all_possible if r not in open_rank_counter]

        conn.execute(text("""
            INSERT INTO best_ranks
            (playtype, position, lookback_n, hit_rank_list, enable,
             total_issues, open_rank_counter, unhit_ranks, created_at)
            VALUES (:playtype, :position, :lookback_n, :hit_rank_list, :enable,
                    :total_issues, :open_rank_counter, :unhit_ranks, :created_at)
        """), dict(
            playtype=query_playtype_name,
            position=position,
            lookback_n=lookback_n,
            hit_rank_list=json.dumps(hit_rank_list, ensure_ascii=False),
            enable=json.dumps(enable, ensure_ascii=False),
            total_issues=total_issues,
            open_rank_counter=json.dumps(open_rank_counter, ensure_ascii=False),
            unhit_ranks=json.dumps(zero_ranks, ensure_ascii=False),
            created_at=datetime.now()
        ))

        log(f"📌 已写 best_ranks：未命中位={zero_ranks}")

    # ✅ 任务执行后再打印一次
    remaining = conn.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")).scalar()
    print(f"待执行任务: {remaining}")

save_log_file_if_needed(log_save_mode=True)
