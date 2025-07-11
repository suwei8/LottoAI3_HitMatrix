#!/usr/bin/env python3
# scripts/analyze_p5_db.py
# 用于全量分析 expert_predictions_p5 数据表结构、玩法、专家数、分布、lookback、排名
# 纯 SQLAlchemy 版

import os
import pandas as pd
from utils.db import get_engine

def analyze_p5_db(max_issues=50):
    engine = get_engine()

    # 1. 查询所有玩法、最大期号、总记录数
    total_rows = pd.read_sql("SELECT COUNT(*) as cnt FROM expert_predictions_p5", engine).iloc[0]["cnt"]
    print(f"总推荐记录数: {total_rows}")

    total_issues = pd.read_sql("SELECT COUNT(DISTINCT issue_name) as cnt FROM expert_predictions_p5", engine).iloc[0]["cnt"]
    print(f"总期号数: {total_issues}")

    total_playtypes = pd.read_sql("SELECT COUNT(DISTINCT playtype_name) as cnt FROM expert_predictions_p5", engine).iloc[0]["cnt"]
    print(f"总玩法数: {total_playtypes}")

    print("\n【玩法期号分布/专家数统计】")
    df = pd.read_sql("""
        SELECT issue_name, playtype_name, COUNT(DISTINCT user_id) as user_cnt, COUNT(*) as rec_cnt
        FROM expert_predictions_p5
        GROUP BY issue_name, playtype_name
        ORDER BY issue_name DESC, playtype_name
    """, engine)
    print(df.head(20))

    print("\n【每个玩法历史期数（lookback_n最大值）】")
    df2 = pd.read_sql("""
        SELECT playtype_name, COUNT(DISTINCT issue_name) as lookback_max
        FROM expert_predictions_p5
        GROUP BY playtype_name
        ORDER BY lookback_max DESC
    """, engine)
    print(df2)

    print("\n【每个玩法单期最大专家数（hit_rank_list最大值）】")
    df3 = pd.read_sql("""
        SELECT playtype_name, MAX(user_cnt) as max_user_cnt
        FROM (
            SELECT playtype_name, issue_name, COUNT(DISTINCT user_id) as user_cnt
            FROM expert_predictions_p5
            GROUP BY playtype_name, issue_name
        ) t
        GROUP BY playtype_name
        ORDER BY max_user_cnt DESC
    """, engine)
    print(df3)

    print("\n【最新10期玩法专家分布】")
    latest_issues = pd.read_sql("""
        SELECT DISTINCT issue_name
        FROM expert_predictions_p5
        ORDER BY issue_name DESC
        LIMIT {}
    """.format(max_issues), engine)["issue_name"].tolist()

    for issue in latest_issues:
        df4 = pd.read_sql(f"""
            SELECT playtype_name, COUNT(DISTINCT user_id) as user_cnt
            FROM expert_predictions_p5
            WHERE issue_name='{issue}'
            GROUP BY playtype_name
            ORDER BY playtype_name
        """, engine)
        print(f"期号: {issue} 玩法专家分布: {df4.to_dict(orient='records')}")

    print("\n【字段样例】")
    df5 = pd.read_sql("SELECT * FROM expert_predictions_p5 LIMIT 1", engine)
    if not df5.empty:
        print(df5.head(1).to_dict(orient='records')[0])
    else:
        print("⚠️ 表是空的，没有样本可展示。")

if __name__ == "__main__":
    analyze_p5_db()
