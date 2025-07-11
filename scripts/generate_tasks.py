# scripts/generate_tasks.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
import json
from datetime import datetime
from sqlalchemy import text
from utils.db import get_engine ,PLAYTYPE_MAPPING
from utils.logger import log
engine = get_engine()

with engine.begin() as conn:
    has_new_task = False  # ✅ 新增标志位

    # ======= 1️⃣ 基础组合 =======
    log("📌 [STEP1] 生成基础组合")
    POSITION_NAME_MAP = {0: "万位", 1: "千位", 2: "百位", 3: "十位", 4: "个位"}

    playtype_en = sys.argv[1] if len(sys.argv) > 1 else "qianwei_ding1"
    playtype_name = PLAYTYPE_MAPPING.get(playtype_en)

    if not playtype_name:
        log(f"❌ 未匹配到中文映射: {playtype_en}")
        sys.exit(1)

    position = None
    for k, v in POSITION_NAME_MAP.items():
        if playtype_name.startswith(v):
            position = k
            break
    if position is None:
        log(f"❌ 未匹配到分位: {playtype_name}")
        sys.exit(1)

    log(f"🎯 当前玩法: {playtype_name} ➜ 分位索引: {position}")

    rows = conn.execute(text("SELECT DISTINCT issue_name FROM lottery_results_p5 ORDER BY issue_name DESC")).fetchall()
    issues = [row[0] for row in rows]
    newest = issues[0]
    oldest = issues[-1]
    max_lookback = int(newest) - int(oldest)
    lookback_ns = list(range(min(max_lookback, 4), 0, -1))
    log(f"🎯 lookback_ns: {lookback_ns}")

    query_playtype_name = playtype_name
    analyze_playtype_name = playtype_name

    for lookback_n in lookback_ns:
        hit_rank_list = [1]
        enable = {"dingwei_sha": [1]}
        skip_if_few = {"dingwei_sha": True}
        resolve_tie_mode = {"dingwei_sha": "Next"}
        reverse_on_tie = {"dingwei_sha": True}

        exist = conn.execute(text("""
            SELECT 1 FROM tasks
            WHERE position=:position
            AND query_playtype_name=:query_playtype_name
            AND analyze_playtype_name=:analyze_playtype_name
            AND lookback_n=:lookback_n
            AND hit_rank_list_first=:hit_rank_list_first
            AND enable_first=:enable_first
        """), dict(
            position=position,
            query_playtype_name=query_playtype_name,
            analyze_playtype_name=analyze_playtype_name,
            lookback_n=lookback_n,
            hit_rank_list_first=hit_rank_list[0],
            enable_first=enable["dingwei_sha"][0]
        )).fetchone()

        if exist:
            log(f"⚠️ 已存在基础组合 ➜ 跳过 lookback_n={lookback_n}")
            continue

        conn.execute(text("""
            INSERT INTO tasks
            (position, query_playtype_name, analyze_playtype_name, lookback_n, hit_rank_list, enable,
             skip_if_few, resolve_tie_mode, reverse_on_tie, status, created_at)
            VALUES (:position, :query_playtype_name, :analyze_playtype_name, :lookback_n, :hit_rank_list, :enable,
                    :skip_if_few, :resolve_tie_mode, :reverse_on_tie, :status, :created_at)
        """), dict(
            position=position,
            query_playtype_name=query_playtype_name,
            analyze_playtype_name=analyze_playtype_name,
            lookback_n=lookback_n,
            hit_rank_list=json.dumps(hit_rank_list, ensure_ascii=False, sort_keys=True),
            enable=json.dumps(enable, ensure_ascii=False, sort_keys=True),
            skip_if_few=json.dumps(skip_if_few, ensure_ascii=False, sort_keys=True),
            resolve_tie_mode=json.dumps(resolve_tie_mode, ensure_ascii=False, sort_keys=True),
            reverse_on_tie=json.dumps(reverse_on_tie, ensure_ascii=False, sort_keys=True),
            status="pending",
            created_at=datetime.now()
        ))
        log(f"✅ 已写入基础组合 lookback_n={lookback_n}")
        has_new_task = True  # ✅ 成功插入

    # ======= 2️⃣ 新增：自动追加 best_ranks 优质组合 =======
    log("📌 [STEP2] 从 best_ranks 追加优质组合")

    rows = conn.execute(text("SELECT * FROM best_ranks")).mappings().all()
    if not rows:
        log("✅ best_ranks 暂无数据，跳过")
    else:
        for row in rows:
            unhit_ranks = json.loads(row["unhit_ranks"])
            unhit_ranks = [r for r in unhit_ranks if r != 1]
            if not unhit_ranks:
                log(f"⚠️ {row['playtype']} 已无可追加 unhit_ranks（仅剩基础组合）")
                continue

            position = row["position"]
            playtype = row["playtype"]
            lookback_n = row["lookback_n"]
            hit_rank_list = json.loads(row["hit_rank_list"])

            query_playtype_name = playtype
            analyze_playtype_name = playtype

            for rank in unhit_ranks:
                enable = {"dingwei_sha": [rank]}
                skip_if_few = {"dingwei_sha": True}
                resolve_tie_mode = {"dingwei_sha": "Next"}
                reverse_on_tie = {"dingwei_sha": True}

                exist = conn.execute(text("""
                    SELECT 1 FROM tasks
                    WHERE position=:position
                    AND query_playtype_name=:query_playtype_name
                    AND analyze_playtype_name=:analyze_playtype_name
                    AND lookback_n=:lookback_n
                    AND hit_rank_list_first=:hr_first
                    AND enable_first=:enable_first
                """), dict(
                    position=position,
                    query_playtype_name=query_playtype_name,
                    analyze_playtype_name=analyze_playtype_name,
                    lookback_n=lookback_n,
                    hr_first=hit_rank_list[0],
                    enable_first=rank
                )).fetchone()

                if exist:
                    log(f"⚠️ 已存在 ➜ 跳过: {playtype} unhit={rank}")
                    continue

                conn.execute(text("""
                    INSERT INTO tasks
                    (position, query_playtype_name, analyze_playtype_name, lookback_n, hit_rank_list, enable,
                     skip_if_few, resolve_tie_mode, reverse_on_tie, status, created_at)
                    VALUES (:position, :query_playtype_name, :analyze_playtype_name, :lookback_n, :hit_rank_list, :enable,
                            :skip_if_few, :resolve_tie_mode, :reverse_on_tie, :status, :created_at)
                """), dict(
                    position=position,
                    query_playtype_name=query_playtype_name,
                    analyze_playtype_name=analyze_playtype_name,
                    lookback_n=lookback_n,
                    hit_rank_list=json.dumps(hit_rank_list, ensure_ascii=False, sort_keys=True),
                    enable=json.dumps(enable, ensure_ascii=False, sort_keys=True),
                    skip_if_few=json.dumps(skip_if_few, ensure_ascii=False, sort_keys=True),
                    resolve_tie_mode=json.dumps(resolve_tie_mode, ensure_ascii=False, sort_keys=True),
                    reverse_on_tie=json.dumps(reverse_on_tie, ensure_ascii=False, sort_keys=True),
                    status="pending",
                    created_at=datetime.now()
                ))

                log(f"✅ 已追加优质组合 ➜ {playtype} unhit={rank}")
                has_new_task = True  # ✅ 成功插入

    if not has_new_task:
        log("🟢 没有新任务插入 ➜ 外层可退出")
    else:
        log("🎉 本轮有新任务 ➜ 外层继续")

