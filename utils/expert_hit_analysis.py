# utils/expert_hit_analysis.py

"""
expert_hit_analysis.py

📌 模块功能简介：

本模块用于分析专家推荐记录的命中表现，并基于统计结果生成杀号、胆码、定位杀号、定位定胆等推荐数字，
具备高度扩展性与灵活性，支持全自动批量分析与策略评估。

🔧 核心功能包括：
- analyze_expert_hits():
    单期专家命中分析函数，支持两种专家筛选模式：
    1）命中排名模式（mode="rank"）：按指定玩法在历史期号中统计命中次数，提取命中排名前N的专家；
    2）命中次数模式（mode="hitcount"）：按多个玩法设置命中次数条件（如 "杀一" ≥ 2）筛选专家。
    支持以下推荐策略：
        - sha1/sha2：杀号（频次前/后数字）
        - dan1/dan2：定胆（频次前/后数字）
        - dingwei_sha1/2/3：定位杀号（指定位置频次统计）
        - dingwei_dan1：定位定胆（指定位置）
    支持指定推荐数字频次排名：[1,2,-1,"prev","prev+1","prev-2"]等复合表达式；
    并提供 tie_mode（并列处理策略）和 skip_flag（推荐不足跳过）等细粒度控制。

- run_hit_analysis_batch():
    支持对多个期号批量执行推荐分析，输出每期推荐、命中结果与总结统计；
    支持跳过策略、回溯不足期、prev定位提取、开奖号码排名追踪等增强能力；
    可传入 log_callback 实现实时日志输出；支持 streamlit.stop 分析中止控制。

- check_hit_on_result():
    提供杀号/胆码/定位杀号/定位定胆等策略的实际命中判断；
    自动对比开奖号执行命中验证，附带详细打印与音效提示（支持本地与浏览器播放）。

- track_open_rank():
    用于统计开奖号码在推荐数字排行榜中的排名位置，辅助评估推荐合理性。

✅ 适用场景：
- Streamlit 页面策略推荐与命中评估
- 脚本定时任务策略效果验证与日志分析
- 自动化测试与策略模型迭代优化
"""



import logging
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.state.session_state_proxy").setLevel(logging.ERROR)

# 本模块支持 Streamlit 页面与脚本环境双模式运行，内部已处理 import streamlit 的兼容封装。
try:
    import streamlit as st
except ImportError:
    class DummyStreamlit:
        session_state = {}
    st = DummyStreamlit()
import os
import pandas as pd
from utils.logger import log, save_log_file_if_needed
import re
from collections import Counter, defaultdict
from utils.db import get_prediction_table, get_result_table
from utils.hit_rule import match_hit



# ⛳ 通用方法：根据给定位置列表提取对应频次的数字
def get_nums_by_positions(sorted_items, positions):
    result = []
    for p in positions:
        if p > 0 and len(sorted_items) >= p:
            result.append(sorted_items[p - 1][0])
        elif p < 0 and len(sorted_items) >= abs(p):
            result.append(sorted_items[p][0])
    return list(set(result))

def should_reverse_on_tie(num_counter: Counter, min_tied: int = 4):
    """
    返回并列数量，只要任意并列 >= min_tied 就触发
    """
    freq_counter = Counter(num_counter.values())
    for count in freq_counter.values():
        if count >= min_tied:
            return count  # 返回具体数量
    return 0



# 主方法：专家推荐命中分析
def analyze_expert_hits(
        engine,  # ✅ 必须放最前面
        lottery_name: str,
        query_issue: str,
        analyze_playtype_name: str = None,
        query_playtype_name: str = None,
        hit_rank_list: list = [2],
        hit_count_conditions: dict = None,
        mode: str = "rank",
        lookback_n: int = None,
        lookback_start_offset: int = 0,
        enable_sha1: list = None,
        enable_sha2: list = None,
        enable_dan1: list = None,
        enable_dan2: list = None,
        enable_dingwei_sha: list = None,
        enable_dingwei_sha2: list = None,
        enable_dingwei_sha3: list = None,
        enable_dingwei_dan1: list = None,   # <----- 新增这一行
        dingwei_sha_pos: int = 2,
        skip_if_few_sha1: bool = True,
        skip_if_few_sha2: bool = True,
        skip_if_few_dan1: bool = True,
        skip_if_few_dan2: bool = True,
        skip_if_few_dingwei_sha: bool = True,
        skip_if_few_dingwei_sha2: bool = True,
        skip_if_few_dingwei_sha3: bool = True,
        skip_if_few_dingwei_dan1: bool = True,

        resolve_tie_mode_sha1: str = "False",
        resolve_tie_mode_sha2: str = "False",
        resolve_tie_mode_dan1: str = "False",
        resolve_tie_mode_dan2: str = "False",
        resolve_tie_mode_dingwei_sha: str = "False",
        resolve_tie_mode_dingwei_sha2: str = "False",
        resolve_tie_mode_dingwei_sha3: str = "False",
        resolve_tie_mode_dingwei_dan1: str = "False",
        reverse_on_tie_dingwei_sha: bool = False,
        reverse_on_tie_dingwei_sha2: bool = False,
        reverse_on_tie_dingwei_sha3: bool = False,
        reverse_on_tie_dingwei_dan1: bool = False,
        specified_user_ids: list = None,  # ✅ 新增：直接指定 user_id
        min_gap_condition: tuple = None,

):
    prediction_table = get_prediction_table(lottery_name)
    result_table = get_result_table(lottery_name)

    issue_df = pd.read_sql(
        f"SELECT DISTINCT issue_name FROM {prediction_table} ORDER BY issue_name DESC",
        engine
    )

    all_issues = issue_df["issue_name"].tolist()

    if query_issue is None:
        query_issue = all_issues[0] if all_issues else None
    prior_issues = [i for i in all_issues if i < query_issue]
    # print(all_issues)
    # print(query_issue)
    issue_list = prior_issues[lookback_start_offset: lookback_start_offset + lookback_n] if lookback_n else prior_issues[lookback_start_offset:]

    # ✅ 如果指定了 user_id，直接使用，跳过后面所有筛选
    if specified_user_ids:
        eligible_user_ids = set(specified_user_ids)
        selected_hit_values = ["指定 user_id"]
        print(f"🎯 查询期号: {query_issue}")
        print(f"🎯 使用指定 user_id 列表: {eligible_user_ids}（跳过自动命中筛选）")

        for uid in list(eligible_user_ids):
            # 查询该 user_id 所有推荐 + 开奖
            df_rec = pd.read_sql(f"""
                SELECT p.issue_name, p.numbers, r.open_code
                FROM {prediction_table} p
                JOIN {result_table} r ON p.issue_name = r.issue_name
                WHERE p.user_id = %s AND p.playtype_name = %s AND p.issue_name < %s
                ORDER BY p.issue_name
            """, engine,  params=(uid, query_playtype_name, query_issue))

            # 真命中期号
            hit_issues = []
            for _, row in df_rec.iterrows():
                if match_hit(query_playtype_name, row["numbers"], row["open_code"], None):
                    hit_issues.append(int(row["issue_name"]))

            if not hit_issues:
                continue

            last_hit = max(hit_issues)
            gap_now = int(query_issue) - last_hit
            if len(hit_issues) >= 2:
                gaps = [j - i for i, j in zip(hit_issues[:-1], hit_issues[1:])]
                avg_gap = sum(gaps) / len(gaps)
                print(f"🔍 user_id: {uid} | 上次命中: {last_hit} | 平均命中间隔: {avg_gap:.2f} | 当前间隔: {gap_now}")
            else:
                print(f"🔍 user_id: {uid} | 上次命中: {last_hit} | 平均命中间隔: 无法计算 | 当前间隔: {gap_now}")


            # ✅ 使用 min_gap_condition 判断
            if min_gap_condition:
                op, val = min_gap_condition
                if eval(f"{gap_now} {op} {val}"):
                    print(f"⚠️ 当前间隔 {gap_now} 满足条件 {op} {val}，跳过 user_id: {uid}")
                    eligible_user_ids.discard(uid)


        if not eligible_user_ids:
            print("⚠️ 所有 user_id 已因最小间隔未达被跳过")
            return build_default_result(query_issue, selected_hit_values)



    else:
        # 后面继续执行原来的模式判断...

        # 如果回溯列表为空，直接返回空结果，防止 SQL 报错
        if not issue_list:
            print("⚠️ 回溯期号列表为空，跳过本期分析。")
            return build_default_result(query_issue, hit_count_conditions if mode == "hitcount" else [])

        print(f"🎯 查询期号: {query_issue}")
        print(f"✅ 彩票类型: {lottery_name}")

        # 模式一：命中次数筛选
        if mode == "hitcount" and hit_count_conditions:
            print("✅ 模式: 命中次数筛选（按玩法条件）")
            print(f"✅ 回溯期号: {issue_list}")
            total_hit_counter_map = defaultdict(Counter)
            for issue in issue_list:
                open_info = pd.read_sql(
                    f"SELECT open_code FROM {result_table} WHERE issue_name = %s",
                    engine, params=(issue,)
                ).to_dict("records")
                if not open_info:
                    continue
                open_code = open_info[0]["open_code"]
                for pt in hit_count_conditions.keys():
                    df = pd.read_sql(
                        f"SELECT user_id, numbers FROM {prediction_table} WHERE issue_name = %s AND playtype_name = %s",
                        engine, params=(issue, pt)
                    )
                    for _, row in df.iterrows():
                        if match_hit(pt, row["numbers"], open_code, None):
                            total_hit_counter_map[pt][row["user_id"]] += 1

            eligible_user_ids = None
            for pt, condition in hit_count_conditions.items():
                op, threshold = condition if isinstance(condition, tuple) else ("==", condition)
                pt_counter = total_hit_counter_map[pt]
                issue_list_str = ",".join([f"'{x}'" for x in issue_list])
                sql = f"""
                  SELECT DISTINCT user_id FROM {prediction_table}
                  WHERE issue_name IN ({issue_list_str}) AND playtype_name = %s
                """
                all_users = pd.read_sql(sql, engine, params=(pt,))

                all_user_ids = set(all_users["user_id"].tolist())
                for uid in all_user_ids:
                    if uid not in pt_counter:
                        pt_counter[uid] = 0
                user_ids_this_pt = [uid for uid, hit in pt_counter.items() if eval(f"{hit} {op} {threshold}")]
                eligible_user_ids = set(user_ids_this_pt) if eligible_user_ids is None else eligible_user_ids & set(user_ids_this_pt)

            if not eligible_user_ids:
                return build_default_result(query_issue, hit_count_conditions)

        # === 命中排名模式 ===
        else:
            print("✅ 模式: 命中排名筛选")
            print(f"🎯 命中次数筛选命中值: {hit_rank_list}")
            print(f"✅ 回溯玩法: {analyze_playtype_name}")
            print(f"✅ 分析玩法: {query_playtype_name}")
            print(f"✅ 回溯期号: {issue_list}")

            # 判断是否是 hit+N 交集模式
            use_single_hit_count_mode = any(isinstance(r, str) and r.startswith("hit+") for r in hit_rank_list)
            exact_hit = None
            if use_single_hit_count_mode:
                for r in hit_rank_list:
                    if isinstance(r, str) and r.startswith("hit+"):
                        exact_hit = int(r.split("+")[1])

            total_hit_counter = Counter()
            per_issue_pass_user_ids = []  # 仅用于 hit+N

            for issue in issue_list:
                # 单期查询
                df = pd.read_sql(
                    f"SELECT user_id, numbers FROM {prediction_table} WHERE issue_name = %s AND playtype_name = %s",
                    engine, params=(issue, analyze_playtype_name)
                )
                open_info = pd.read_sql(
                    f"SELECT open_code FROM {result_table} WHERE issue_name = %s",
                    engine, params=(issue,)
                ).to_dict("records")
                if not open_info:
                    continue
                open_code = open_info[0]["open_code"]
                open_nums = set(map(int, re.findall(r"\d+", open_code)))

                if use_single_hit_count_mode:
                    pass_user_ids_this_issue = set()
                    for _, row in df.iterrows():
                        rec_nums = set(map(int, re.findall(r"\d+", row["numbers"])))
                        hit_cnt = len(rec_nums & open_nums)
                        if hit_cnt == exact_hit:
                            pass_user_ids_this_issue.add(row["user_id"])
                    per_issue_pass_user_ids.append(pass_user_ids_this_issue)
                else:
                    for _, row in df.iterrows():
                        if match_hit(analyze_playtype_name, row["numbers"], open_code, None):
                            total_hit_counter[row["user_id"]] += 1

            if use_single_hit_count_mode:
                if per_issue_pass_user_ids:
                    eligible_user_ids = set.intersection(*per_issue_pass_user_ids)
                else:
                    eligible_user_ids = set()
                selected_hit_values = [exact_hit]
            else:
                user_hit_dict = dict(total_hit_counter)
                issue_list_str = ",".join([f"'{x}'" for x in issue_list])
                sql = f"""
                        SELECT DISTINCT user_id FROM {prediction_table}
                        WHERE issue_name IN ({issue_list_str}) AND playtype_name = %s
                    """
                all_expert_df = pd.read_sql(sql, engine, params=(analyze_playtype_name,))
                all_user_ids = set(all_expert_df["user_id"])
                for uid in all_user_ids:
                    if uid not in user_hit_dict:
                        user_hit_dict[uid] = 0
                hit_values = sorted(set(user_hit_dict.values()), reverse=True)

                selected_hit_values = []
                for r in hit_rank_list:
                    if isinstance(r, int) and abs(r) <= len(hit_values):
                        selected_hit_values.append(hit_values[r - 1] if r > 0 else hit_values[r])
                eligible_user_ids = [uid for uid, hit in user_hit_dict.items() if hit in selected_hit_values]

            print(f"🎯 最终解析出的命中值筛选列表: {selected_hit_values} （命中排名/命中值）")
            print(f"🎯 AI参与数量: {len(eligible_user_ids)}")

            if not eligible_user_ids:
                return build_default_result(query_issue, selected_hit_values)


    # 查询推荐数据
    sql = f"""
        SELECT user_id, numbers
        FROM {prediction_table}
        WHERE issue_name = %s AND playtype_name = %s
          AND user_id IN ({','.join(['%s'] * len(eligible_user_ids))})
    """
    params = (query_issue, query_playtype_name, *list(eligible_user_ids))
    rec_df = pd.read_sql(sql, engine, params=params)

    # 提取所有推荐数字
    all_numbers = []
    for nums in rec_df["numbers"]:
        digits = re.findall(r"\d+", nums)
        all_numbers.extend(map(int, digits))
    num_counter = Counter(all_numbers)

    print("🎯 推荐数字排行榜:")
    for num, count in num_counter.most_common():
        print(f"数字 {num}: 出现 {count} 次")

    sorted_items = num_counter.most_common()

    # ✅ 新增：用于 prev 策略的“上期开奖号”
    prev_open_code_str = None
    try:
        prev_issue = str(int(query_issue) - 1)
        df_prev_open = pd.read_sql(
            f"SELECT open_code FROM {result_table} WHERE issue_name = %s",
            engine, params=(prev_issue,)
        )

        if not df_prev_open.empty:
            prev_open_code_str = df_prev_open.iloc[0]["open_code"]
            print(f"🎯 上期开奖号（用于 prev 策略）：{prev_issue}，开奖号：{prev_open_code_str}")
        else:
            print(f"⚠️ 上期开奖号未找到，将跳过所有 prev 策略相关提取")
    except Exception as e:
        print(f"❌ 获取上期开奖结果失败: {e}")

    # 追踪开奖号码在推荐频次排序中的排名
    open_code_str = None
    df_open = pd.read_sql(
        f"SELECT open_code FROM {result_table} WHERE issue_name = %s",
        engine, params=(query_issue,)
    )

    if not df_open.empty:
        open_code_str = df_open.iloc[0]["open_code"]

    def extract_strategy(name, enable_list, skip_flag, tie_mode="False", open_code_str=None, dingwei_sha_pos=2, reverse_on_tie=False):
        if not enable_list:
            return None
        if len(sorted_items) < 5 and skip_flag:
            return None
        # 如果包含 "All"，直接输出全量推荐数字
        if enable_list == "All" or (isinstance(enable_list, list) and "All" in enable_list):
            all_nums = [num for num, _ in sorted_items]
            print(f"🔥 {name} 共提取{len(all_nums)}个数字（All模式）：{all_nums}")
            return list(set(all_nums))


        result = []

        for pos_expr in enable_list:
            sub_positions = [s.strip() for s in str(pos_expr).split(",")]
            extracted = False

            for sub_pos in sub_positions:

                if sub_pos.startswith("prev"):
                    match = re.match(r"prev([+-]?\d*)", sub_pos)
                    offset = int(match.group(1)) if match and match.group(1) else 0

                    if not open_code_str:
                        print(f"⚠️ 无法提取 prev 位置数字（开奖号码为空）")
                        continue

                    try:
                        open_digits = list(map(int, open_code_str.strip().split(",")))
                        target_digit = open_digits[dingwei_sha_pos]
                        ranked_nums = [num for num, _ in sorted_items]

                        if target_digit not in ranked_nums:
                            print(f"⚠️ prev策略：上期数字 [{target_digit}] 不在推荐排行榜中，尝试备用")
                            continue

                        idx = ranked_nums.index(target_digit)
                        new_idx = (idx + offset) % len(ranked_nums)
                        selected_num = ranked_nums[new_idx]
                        selected_val = num_counter[selected_num]

                        # 这里对比 selected_val 有多少个并列
                        tied = [n for n in ranked_nums if num_counter[n] == selected_val]
                        global_tied_count = should_reverse_on_tie(num_counter)
                        # “全局出现某个频次相同的数字 ≥ 4个” 触发反向 ± 偏移
                        if global_tied_count >= 4 and reverse_on_tie:
                            print(f"⚠️ prev触发反向：当前全局频次并列达到 {global_tied_count} 个，触发反向 ± 偏移")
                            offset = -offset
                            new_idx = (idx + offset) % len(ranked_nums)
                            selected_num = ranked_nums[new_idx]
                            print(f"🎯 prev反向提取 wrap后：上期[{target_digit}] ±{abs(offset)} ⇒ {selected_num}")
                            result.append(selected_num)
                            extracted = True
                        else:
                            print(f"🎯 prev提取：上期[{target_digit}] {offset:+} ⇒ {selected_num}")
                            result.append(selected_num)
                            extracted = True

                    except Exception as e:
                        print(f"❌ prev提取异常：{e}")

                    if extracted:
                        break

                else:
                    try:
                        idx = int(sub_pos) - 1 if int(sub_pos) > 0 else int(sub_pos)
                        if abs(idx) >= len(sorted_items):
                            continue

                        target_val = sorted_items[idx][1]
                        tied = [num for num, cnt in sorted_items if cnt == target_val]

                        if len(tied) > 1 and tie_mode == "Skip":
                            print(f"⚠️ {name} 出现并列，跳过")
                            continue

                        elif len(tied) > 1 and tie_mode == "Next":
                            for next_idx in range(idx + 1, len(sorted_items)):
                                if sorted_items[next_idx][1] != target_val:
                                    result.append(sorted_items[next_idx][0])
                                    print(f"🎯 {name} 跳过并列，选第 {next_idx + 1} 名")
                                    extracted = True
                                    break

                        elif len(tied) > 1 and reverse_on_tie:
                            if idx >= 0:
                                new_idx = -1 * (idx + 1)
                            else:
                                new_idx = abs(idx) - 1  # 理论上没必要，除非你传负数
                            if abs(new_idx) >= len(sorted_items):
                                continue
                            num = sorted_items[new_idx][0]
                            print(f"⚠️ {name} 出现并列，reverse_on_tie=True，原 idx={idx+1} → 反向 idx={new_idx} → {num}")
                            result.append(num)
                            extracted = True

                        else:
                            result.append(sorted_items[idx][0])
                            print(f"🔥 {name} 提取第 {idx + 1 if idx >= 0 else len(sorted_items) + idx + 1} 名：{sorted_items[idx][0]}")
                            extracted = True
                    except Exception as e:
                        print(f"❌ 排名提取异常：{e}")
                    if extracted:
                        break

        return list(set(result)) if result else None


    # 仅跳过配置为跳的策略，其他照常执行
    strategy_enabled = {
        "sha1": bool(enable_sha1),
        "sha2": bool(enable_sha2),
        "dan1": bool(enable_dan1),
        "dan2": bool(enable_dan2),
        "dingwei_sha": bool(enable_dingwei_sha),
        "dingwei_sha2": bool(enable_dingwei_sha2),
        "dingwei_sha3": bool(enable_dingwei_sha3),
        "dingwei_dan1": bool(enable_dingwei_dan1),
    }

    strategy_skip_config = {
        "sha1": skip_if_few_sha1,
        "sha2": skip_if_few_sha2,
        "dan1": skip_if_few_dan1,
        "dan2": skip_if_few_dan2,
        "dingwei_sha": skip_if_few_dingwei_sha,
        "dingwei_sha2": skip_if_few_dingwei_sha2,
        "dingwei_sha3": skip_if_few_dingwei_sha3,
        "dingwei_dan1": skip_if_few_dingwei_dan1,
    }

    if len(sorted_items) < 5:
        skipped = []
        for name in strategy_enabled:
            if strategy_enabled[name] and strategy_skip_config[name]:
                skipped.append(name)
        if skipped:
            print("⚠️ 推荐数字少于5个，以下策略将被跳过：")
            for name in skipped:
                print(f"  - {name}")

    sha1 = extract_strategy("sha1", enable_sha1, skip_if_few_sha1, resolve_tie_mode_sha1, prev_open_code_str, dingwei_sha_pos)
    sha2 = extract_strategy("sha2", enable_sha2, skip_if_few_sha2, resolve_tie_mode_sha2, prev_open_code_str, dingwei_sha_pos)
    dan1 = extract_strategy("dan1", enable_dan1, skip_if_few_dan1, resolve_tie_mode_dan1, prev_open_code_str, dingwei_sha_pos)
    dan2 = extract_strategy("dan2", enable_dan2, skip_if_few_dan2, resolve_tie_mode_dan2, prev_open_code_str, dingwei_sha_pos)
    dingwei_sha  = extract_strategy("dingwei_sha", enable_dingwei_sha, skip_if_few_dingwei_sha, resolve_tie_mode_dingwei_sha, prev_open_code_str, dingwei_sha_pos, reverse_on_tie_dingwei_sha)
    dingwei_sha2 = extract_strategy("dingwei_sha2", enable_dingwei_sha2, skip_if_few_dingwei_sha2, resolve_tie_mode_dingwei_sha2, prev_open_code_str, dingwei_sha_pos, reverse_on_tie_dingwei_sha2)
    dingwei_sha3 = extract_strategy("dingwei_sha3", enable_dingwei_sha3, skip_if_few_dingwei_sha3, resolve_tie_mode_dingwei_sha3, prev_open_code_str, dingwei_sha_pos, reverse_on_tie_dingwei_sha3)
    dingwei_dan  = extract_strategy("dingwei_dan1", enable_dingwei_dan1, skip_if_few_dingwei_dan1, resolve_tie_mode_dingwei_dan1, prev_open_code_str, dingwei_sha_pos, reverse_on_tie_dingwei_dan1)


    return {
        "rec_df": rec_df,
        "user_ids": list(eligible_user_ids),
        "num_counter": num_counter,
        "sha1": sha1,
        "sha2": sha2,
        "dan1": dan1,
        "dan2": dan2,
        "dingwei_sha": dingwei_sha,
        "dingwei_sha2": dingwei_sha2,
        "dingwei_sha3": dingwei_sha3,
        "dingwei_dan": dingwei_dan,           # <--- 新增
        "min_hit_threshold": hit_count_conditions if mode == "hitcount" else selected_hit_values,
        "query_issue": query_issue,
        "open_code": open_code_str
    }

# 辅助：构造空结果结构
def build_default_result(query_issue, hit_threshold):
    return {
        "rec_df": pd.DataFrame(),
        "user_ids": [],
        "num_counter": Counter(),
        "sha1": None,
        "sha2": None,
        "dan1": None,
        "dan2": None,
        "dingwei_sha": None,
        "dingwei_sha2": None,
        "dingwei_sha3": None,
        "dingwei_dan": None,   # <--- 新增这一行，保持结构一致
        "min_hit_threshold": hit_threshold,
        "query_issue": query_issue
    }
# ✅ 判断是否处于 Streamlit 环境
def in_streamlit_context():
    try:
        import streamlit.runtime.scriptrunner.script_run_context as script_ctx
        return script_ctx.get_script_run_ctx() is not None
    except Exception:
        return False

# ✅ 命中判断函数：杀号 / 胆码 / 定位杀号
def check_hit_on_result(engine, lottery_name, issue_name,
                        sha_list=None, dan_list=None,
                        dingwei_sha=None, dingwei_sha2=None, dingwei_sha3=None,
                        dingwei_dan=None,    # <--- 新增参数
                        dingwei_sha_pos=None,
                        check_mode="dingwei",
                        rec_df=None):
    if dingwei_sha_pos is None and check_mode == "dingwei":
        print("✅ 未启用定位策略，已跳过定位判断")
        return True

    from utils.db import get_result_table
    result_table = get_result_table(lottery_name)

    # 读取开奖号码
    df_open = pd.read_sql(
        f"SELECT open_code FROM {result_table} WHERE issue_name = %s",
        engine, params=(issue_name,)
    )
    if df_open.empty:
        print("⚠️ 未找到开奖号码")
        raise ValueError("open_code_missing")


    open_code = df_open.iloc[0]["open_code"]
    print(f"🎯 当期开奖号码: {open_code}")
    open_digits = set(map(int, open_code.strip().split(",")))
    open_digits_list = list(map(int, open_code.strip().split(",")))
    POSITION_NAME_MAP = {}
    if lottery_name in ["排列5", "排列五"]:
        POSITION_NAME_MAP = {0: "万位", 1: "千位", 2: "百位", 3: "十位", 4: "个位"}
    else:
        POSITION_NAME_MAP = {0: "百位", 1: "十位", 2: "个位"}
    hit_success = True  # ✅ 统一统计用：若任一判断失败则设为 False

    # 杀号判断
    if sha_list:
        for i, sha in enumerate(sha_list, start=1):
            if sha is None:
                continue
            if isinstance(sha, list):
                total_count = len(sha)
                hit_nums = [s for s in sha if s in open_digits]
                if hit_nums:
                    print(f"❌ 杀号失败 {i} 共提取{total_count}个数字：【{sha}】命中开奖号码 {hit_nums} ❗")
                    # 👇 追加查找 user_id
                    if rec_df is not None:
                        for _, row in rec_df.iterrows():
                            nums = [int(n.strip()) for n in row["numbers"].split(",") if n.strip().isdigit()]
                            if any(hit in nums for hit in hit_nums):
                                print(f"🔍 命中来源 user_id: {row['user_id']}")
                    hit_success = False
                else:
                    print(f"✅ 杀号成功 {i} 共提取{total_count}个数字：【{sha}】未命中（正确）")
            else:
                total_count = 1
                if sha in open_digits:
                    print(f"❌ 杀号失败 {i} 共提取{total_count}个数字：【[{sha}]】命中开奖号码 [{sha}] ❗")
                    hit_success = False
                else:
                    print(f"✅ 杀号成功 {i} 共提取{total_count}个数字：【[{sha}]】未命中（正确）")


    # 胆码判断
    if dan_list:
        for i, dan in enumerate(dan_list, start=1):
            if not dan:
                continue
            dan_values = dan if isinstance(dan, list) else [dan]
            if any(d in open_digits for d in dan_values):
                print(f"✅ 定胆成功 {i}【{dan_values}】命中开奖号码 ✅")
            else:
                print(f"❌ 胆号失败 {i}【{dan_values}】未命中 ❌")
                hit_success = False

    # 定位杀号判断
    merged_dingwei_sha = set()
    if check_mode == "all":
        positions = list(range(len(open_digits_list)))
    else:
        positions = [dingwei_sha_pos]
    if dingwei_sha:
        merged_dingwei_sha.update(dingwei_sha)
    if dingwei_sha2:
        merged_dingwei_sha.update(dingwei_sha2)
    if dingwei_sha3:
        merged_dingwei_sha.update(dingwei_sha3)

    if merged_dingwei_sha:
        for pos in positions:
            if len(open_digits_list) <= pos:
                print(f"⚠️ 开奖号码位数不足，无法执行定位杀号判断（定位位：{pos}）")
                continue
            target_digit = open_digits_list[pos]
            if target_digit in merged_dingwei_sha:
                pos_name = POSITION_NAME_MAP.get(pos, f"{pos}位")
                print(f"❌ 定位杀号失败（开奖号码-{pos_name}数字[{target_digit}] 在杀号列表 {sorted(merged_dingwei_sha)} 中）❗")
                hit_success = False
                break
        else:
            # ✅ 所有位置均未命中，才是成功
            pos_msgs = []
            for pos in positions:
                if len(open_digits_list) > pos:
                    pos_name = POSITION_NAME_MAP.get(pos, f"{pos}位")
                    pos_digit = open_digits_list[pos]
                    pos_msgs.append(f"{pos_name}数字[{pos_digit}]")

            msg = "、".join(pos_msgs)
            print(f"✅ 定位杀号成功（杀号数字 {sorted(merged_dingwei_sha)} 未在开奖号码-{msg}中）")


    # 定位定胆判断
    if dingwei_dan:
        for pos in positions:
            if len(open_digits_list) <= pos:
                print(f"⚠️ 开奖号码位数不足，无法执行定位定胆判断（定位位：{pos}）")
                continue
            target_digit = open_digits_list[pos]
            if target_digit in dingwei_dan:
                print(f"✅ 定位定胆命中（开奖号码第 {pos} 位为 {target_digit}，在定胆列表 {sorted(dingwei_dan)} 中）")
            else:
                print(f"❌ 定位定胆未命中（开奖号码第 {pos} 位为 {target_digit}，不在定胆列表 {sorted(dingwei_dan)} 中）❗")
                hit_success = False
                break

    return hit_success

# ✅ 辅助函数：追踪开奖号码在推荐数字频次排序中的排名位置
def track_open_rank(result: dict, dingwei_sha_pos: int, rank_counter: Counter, check_mode="dingwei"):
    """
    用于统计开奖号码中指定位置数字在推荐数字频次排序中的排名。
    """
    sorted_items = [num for num, _ in result.get("num_counter", {}).most_common()]
    open_code_str = result.get("open_code")
    if not open_code_str:
        return

    open_digits = list(map(int, open_code_str.strip().split(",")))
    if dingwei_sha_pos is None and check_mode != "all":
        return  # 如果没有定位位且不是全位模式，直接跳过
    positions = [dingwei_sha_pos] if check_mode != "all" else list(range(len(open_digits)))

    if check_mode == "all":
        positions = list(range(len(open_digits)))

    for pos in positions:
        if len(open_digits) <= pos:
            continue
        digit = open_digits[pos]
        if digit in sorted_items:
            try:
                rank = sorted_items.index(digit) + 1
                rank_counter[rank] += 1
            except ValueError:
                print(f"⚠️ 开奖号码 {digit} 未出现在推荐排序列表中，跳过统计。")

def run_hit_analysis_batch(
        engine,
        lottery_name,
        query_issues,
        enable_hit_check,
        enable_track_open_rank,
        dingwei_sha_pos,
        check_mode,
        analysis_kwargs: dict,
        stop_flag_key="stop_analysis",  # ✅ 新增参数
        log_callback=None,  # ✅ 新增参数
        all_mode_limit: int = None,
        strategy_relative_path=None   # ✅ 新增
):
    """
    分析指定多个期号的杀号/胆码/定位杀号效果，并支持命中率与推荐数字排名统计。

    参数：
    - engine: 数据库连接对象
    - lottery_name: 彩种名，如 '福彩3D'
    - query_issues: 要分析的期号列表
    - enable_hit_check: 是否执行 check_hit_on_result 判断
    - enable_track_open_rank: 是否启用开奖号码推荐排名统计
    - dingwei_sha_pos: 定位杀号的目标位（0=百, 1=十, 2=个）
    - analysis_kwargs: 要传给 analyze_expert_hits 的其他参数（dict）
    - check_mode: str = "dingwei"   # 定位杀号判断模式：仅指定位置（"dingwei"）或全位判断（"all"）

    返回：
    - None（仅打印分析结果）
    """
    from collections import Counter
    global print
    print = log  # ✅ 重定向 print 到 log，实现捕获
    from collections import Counter
    miss_count = 0            # 未命中次数
    skip_count = 0            # ✅ 新增：跳过本期（推荐不足或回溯为空）
    open_rank_counter = Counter()  # ✅ 累计开奖号码在推荐频次中出现的排名
    # print(f"🟢 lookback_n (batch) = {analysis_kwargs.get('lookback_n')}")
    # ✅ 支持 query_issues = ['All']，自动提取所有期号
    if query_issues == ["All"]:
        prediction_table = get_prediction_table(lottery_name)
        issue_df = pd.read_sql(
            f"SELECT DISTINCT issue_name FROM {prediction_table} ORDER BY issue_name DESC",
            engine
        )
        query_issues = issue_df["issue_name"].tolist()
        if all_mode_limit is not None:
            query_issues = query_issues[:all_mode_limit]
            print(f"✅ 已限制仅保留最新 {all_mode_limit} 期")
        print(f"✅ query_issues = ['All'] 模式生效，共提取期号数量：{len(query_issues)}")
        # print(f"📋 期号列表：{query_issues}")

    max_rank_length = 0
    for query_issue in query_issues:
        try:
            if in_streamlit_context() and st.session_state.get(stop_flag_key, False):
                print("🛑 检测到用户请求中止分析，任务已终止！")
                if log_callback:
                    log_callback()
                break
        except Exception:
            pass

        print("=" * 16)
        print()
        # print(f"🎯 开始分析期号：{query_issue}")
        if log_callback:
            log_callback()

        result = analyze_expert_hits(
            engine=engine,
            lottery_name=lottery_name,
            query_issue=query_issue,
            dingwei_sha_pos=dingwei_sha_pos,
            **analysis_kwargs
        )

        rank_length = len(result.get("num_counter", {}))
        if rank_length > max_rank_length:
            max_rank_length = rank_length

        # ✅ 判断回溯期为空或推荐数字不足的跳过情况
        if result is None or result.get("rec_df") is None or result["rec_df"].empty:
            # print("⚠️ 回溯为空或推荐数字过少，跳过本期分析。")
            skip_count += 1
            continue
        if result.get("dan1") is not None:
            print(f"🔥 胆号1（高频唯一）: {result['dan1']}")
        if result.get("dan2") is not None:
            print(f"🔥 胆号2（次高频唯一）: {result['dan2']}")
        if result.get("dingwei_dan") is not None:         # <--- 这里加
            print(f"🔥 定位定胆1: {result['dingwei_dan']}")  # <--- 这里加
        if log_callback:
            log_callback()

        combined_dingwei_sha = []
        for key in ["dingwei_sha", "dingwei_sha2", "dingwei_sha3"]:
            val = result.get(key)
            if val:
                combined_dingwei_sha.extend(val)
        if combined_dingwei_sha:
            combined_dingwei_sha = sorted(set(combined_dingwei_sha))
            print(f"🔥 定位杀号: {combined_dingwei_sha}")
            if log_callback:
                log_callback()

        if enable_hit_check:
            try:
                hit_result = check_hit_on_result(
                    engine, lottery_name,
                    result["query_issue"],
                    sha_list=[result["sha1"], result["sha2"]],
                    rec_df=result["rec_df"],
                    dan_list=[result.get("dan1"), result.get("dan2")],
                    dingwei_sha=result.get("dingwei_sha"),
                    dingwei_sha2=result.get("dingwei_sha2"),
                    dingwei_sha3=result.get("dingwei_sha3"),
                    dingwei_sha_pos=dingwei_sha_pos,
                    check_mode=check_mode,
                    dingwei_dan=result.get("dingwei_dan"),
                )
                if log_callback:
                    log_callback()

                if enable_track_open_rank:
                    track_open_rank(result, dingwei_sha_pos, open_rank_counter, check_mode=check_mode)

                if hit_result is False:
                    miss_count += 1
            except ValueError as e:
                if str(e) == "open_code_missing":
                    print("⚠️ 未找到开奖号码，跳过本期统计")
                    skip_count += 1
                    continue
                else:
                    raise

    # ✅ 循环结束后打印总统计
    if enable_hit_check:
        print("=" * 50)
        total_issues = len(query_issues)
        hit_count = total_issues - miss_count - skip_count
        print(f"📉 共 {total_issues} 期，未命中次数：{miss_count} 期，跳过 {skip_count} 期")
        print(f"✅ 命中率：{hit_count} / {total_issues}")
        print(f"策略配置文件：{strategy_relative_path}")   # ✅ 直接一起 print
    if enable_track_open_rank:
        print("📊 开奖号码在推荐数字频次排序中的排名统计：")
        # 用max_rank_length，而不是max(open_rank_counter.keys())
        all_possible_ranks = list(range(1, max_rank_length + 1))
        zero_ranks = [r for r in all_possible_ranks if r not in open_rank_counter]

        if zero_ranks:
            zero_ranks_str = ",".join([str(r) for r in zero_ranks])
            print(f"   - 未命中排名位：{zero_ranks_str}")

        for rank in sorted(open_rank_counter):
            print(f"   - 排名第 {rank} 位：{open_rank_counter[rank]} 次")
            print("=" * 30)

    if log_callback:
        log_callback()

    return {
        "total_issues": len(query_issues),
        "miss_count": miss_count,
        "skip_count": skip_count,
        "open_rank_counter": open_rank_counter,   # ✅ 新增
        "max_rank_length": max_rank_length        # ✅ 新增
    }


def load_user_ids_from_file(filename="user_id.txt"):
    """
    尝试从脚本目录下加载 user_id.txt 文件，每行一个 user_id。
    :param filename: 文件名（默认 user_id.txt）
    :return: List[int] 或 None
    """
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
        user_ids = [int(line.strip()) for line in lines if line.strip().isdigit()]
        print(f"✅ 从 {filename} 加载了 {len(user_ids)} 个 user_id")
        return user_ids
    else:
        print(f"📌 未找到 {filename}，使用默认指定列表")
        return None