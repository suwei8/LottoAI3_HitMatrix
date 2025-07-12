# scripts/generate_tasks.py
"""
📌 脚本名称：generate_tasks.py
🧠 脚本简介：
我是 LottoAI3_HitMatrix 项目的任务生成器，专用于从 expert_predictions_p5 数据表中自动挖掘可用于回测分析的组合参数，并将其写入 tasks 表中，供后续分析模块使用。

🔍 功能亮点：
1️⃣ 基础组合生成：根据指定玩法（如 “千位定1”）及其分位索引，遍历全部可用期号并依次构造不同回溯期数（lookback_n）的任务组合；
2️⃣ 高命中优选扩展：自动读取 best_ranks 表中的优质推荐组合，排除基础组合已包含的部分，补充命中表现优异的 rank 组合，提高后续分析命中率潜力；
3️⃣ 去重插入保障：避免重复插入相同配置的任务记录，通过多字段精确比对确保数据库整洁；
4️⃣ 全流程日志输出：每一步执行流程都具备清晰的日志记录，便于调试与追踪；

📥 入参：
- 命令行参数 1：玩法英文名（如 qianwei_ding1），默认值为 "qianwei_ding1"

📤 输出：
- 向 tasks 表插入符合条件的待分析任务（状态为 pending）

🧩 依赖模块：
- utils.db ➜ 数据库连接及玩法映射
- utils.logger ➜ 日志输出封装

✨ 用法示例：
python scripts/generate_tasks.py wanwei_ding1

✅ 本脚本作为 LottoAI3 分析流水线的第一环节，自动准备可回测任务，是构建“高命中率组合搜索器”的关键组件。
"""

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

    rows = conn.execute(text("""
        SELECT DISTINCT issue_name
        FROM expert_predictions_p5
        WHERE playtype_name = :playtype_name
        ORDER BY issue_name DESC
    """), {"playtype_name": playtype_name}).fetchall()

    issues = [row[0] for row in rows]

    if not issues:
        log(f"❌ expert_predictions_p5 中无可用预测记录 ➜ {playtype_name}")
        sys.exit(1)

    lookback_ns = list(range(len(issues), 0, -1))  # ✅ 全部回溯
    log(f"🎯 当前玩法: {playtype_name} ➜ 可用预测期数={len(issues)} ➜ lookback_ns: {lookback_ns}")

    query_playtype_name = playtype_name
    analyze_playtype_name = playtype_name

    hit_rank_combinations = [
        [1],
        [2],
        [3],
        [1,2,3],
    ]

    for lookback_n in lookback_ns:
        for rank in range(1, 11):  # 1 ~ 10
            for hit_rank_list in hit_rank_combinations:
                enable = {"dingwei_sha": [rank]}
                skip_if_few = {"dingwei_sha": False}
                resolve_tie_mode = {"dingwei_sha": "False"}
                reverse_on_tie = {"dingwei_sha": False}

                exist = conn.execute(text("""
                    SELECT 1 FROM tasks
                    WHERE analyze_playtype_name=:analyze_playtype_name
                    AND lookback_n=:lookback_n
                    AND enable_first=:enable_first
                """), dict(
                    analyze_playtype_name=analyze_playtype_name,
                    lookback_n=lookback_n,
                    enable_first=rank
                )).fetchone()

                if exist:
                    log(f"⚠️ 已存在基础组合 ➜ 跳过 lookback_n={lookback_n} ➜ rank={rank} ➜ hit_rank_list={hit_rank_list}")
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

                log(f"✅ 已写入基础组合 ➜ lookback_n={lookback_n} ➜ rank={rank} ➜ hit_rank_list={hit_rank_list}")
                has_new_task = True

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



