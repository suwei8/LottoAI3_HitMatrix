import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from utils.db import get_engine

def generate_wechat_message(run_number, playtype_cn, issue_start, issue_end, issue_count,
                            task_pool, qualified_pool, level_pool, mins, secs, upload_time=None):
    time_str = f"🕒 上传时间：\n {upload_time}" if upload_time else ""
    return (
        f"🎰 排列5-HitMatrix任务报告\n"
        f"【Actions 运行编号:#{run_number}】\n"
        f"🎯 玩法: {playtype_cn}\n"
        f"\n"
        f"📅 分析期号范围: {issue_start}-{issue_end}\n"
        f"📊 分析期数: {issue_count}\n"
        f"\n"
        f"✅ 组合任务池数量：{task_pool}\n"
        f"✅ 达标组合池数量：{qualified_pool}\n"
        f"✅ 层级排名池数量：{level_pool}\n"
        f"📌 耗时：{mins}分{secs}秒\n"
        f"{time_str}"
    )

def send_wechat_message(playtype_cn: str):
    run_number = os.getenv("GITHUB_RUN_NUMBER", "DEV")
    mins = os.getenv("DURATION_MINUTES", "0")
    secs = os.getenv("DURATION_SECONDS", "0")

    # 获取北京时间
    now_bj = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=8)
    now_str = now_bj.strftime("%Y-%m-%d %H:%M:%S")

    print(f"📦 耗时: {mins}分 {secs}秒，上传时间: {now_str}")

    engine = get_engine()
    with engine.connect() as conn:
        issue_start, issue_end = conn.execute(text(
            "SELECT MAX(issue_name), MIN(issue_name) FROM lottery_results_p5"
        )).fetchone()
        issue_count = conn.execute(text("SELECT COUNT(DISTINCT issue_name) FROM lottery_results_p5")).scalar()
        task_pool = conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar()
        qualified_pool = conn.execute(text("SELECT COUNT(*) FROM best_tasks")).scalar()
        level_pool = conn.execute(text("SELECT COUNT(*) FROM best_ranks")).scalar()

    msg = generate_wechat_message(
        run_number=run_number,
        playtype_cn=playtype_cn,
        issue_start=issue_start,
        issue_end=issue_end,
        issue_count=issue_count,
        task_pool=task_pool,
        qualified_pool=qualified_pool,
        level_pool=level_pool,
        mins=mins,
        secs=secs,
        upload_time=now_str
    )

    print("✅ 即将发送内容：")
    print(msg)

    response = requests.post(
        os.getenv("WECHAT_API_URL"),
        headers={"Content-Type": "application/json", "x-api-key": os.getenv("WECHAT_API_KEY")},
        json={"content": msg}
    )

    print(f"✅ 已发送，状态码：{response.status_code}")
    print(f"返回：{response.text}")

if __name__ == "__main__":
    playtype_cn = sys.argv[1] if len(sys.argv) > 1 else "未指定玩法"
    send_wechat_message(playtype_cn)
