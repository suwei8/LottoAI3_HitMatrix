# utils/report_tools.py

def generate_wechat_message(run_number, playtype_cn, issue_start, issue_end, issue_count,
                            task_pool, qualified_pool, level_pool, mins, secs):
    return (
        f"🎰 排列5-HitMatrix任务报告\n"
        f"【Actions 运行编号:#{run_number}】\n"
        f" 🎯 玩法: {playtype_cn}\n"
        f"\n"
        f"📅 分析期号范围: {issue_start}-{issue_end}\n"
        f"📊 分析期数: {issue_count}\n"
        f"\n"
        f"✅ 组合任务池数量：{task_pool}\n"
        f"✅ 达标组合池数量：{qualified_pool}\n"
        f"✅ 层级排名池数量：{level_pool}\n"
        f"📌 耗时：{mins}分{secs}秒"
    )
