import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
import requests
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from utils.db import (
    get_engine,
    get_tasks_table,
    get_best_tasks_table,
    get_best_ranks_table,
    get_result_table,
)

def generate_wechat_message(run_number, playtype_cn, issue_start, issue_end, issue_count,
                            task_pool, qualified_pool, level_pool, mins, secs,
                            lottery_name="排列5", upload_time=None):
    time_str = f"🕒 上传时间：\n {upload_time}" if upload_time else ""
    return (
        f"🎰 {lottery_name}-HitMatrix任务报告\n"
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

def send_wechat_message(playtype_cn: str, lottery_type: str = "p5"):
    run_number = os.getenv("GITHUB_RUN_NUMBER", "DEV")
    mins = os.getenv("DURATION_MINUTES", "0")
    secs = os.getenv("DURATION_SECONDS", "0")
    # 动态获取表名
    lottery_name = "排列5" if lottery_type == "p5" else "福彩3D"

    result_table = get_result_table(lottery_name)
    tasks_table = get_tasks_table(lottery_name)
    best_tasks_table = get_best_tasks_table(lottery_name)
    best_ranks_table = get_best_ranks_table(lottery_name)

    # 获取北京时间
    now_bj = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=8)
    now_str = now_bj.strftime("%Y-%m-%d %H:%M:%S")

    print(f"📦 耗时: {mins}分 {secs}秒，上传时间: {now_str}")

    engine = get_engine()
    with engine.connect() as conn:
        issue_start, issue_end = conn.execute(
            text(f"SELECT MAX(issue_name), MIN(issue_name) FROM {result_table}")
        ).fetchone()
        issue_count = conn.execute(
            text(f"SELECT COUNT(DISTINCT issue_name) FROM {result_table}")
        ).scalar()
        task_pool = conn.execute(text(f"SELECT COUNT(*) FROM {tasks_table}")).scalar()
        qualified_pool = conn.execute(text(f"SELECT COUNT(*) FROM {best_tasks_table}")).scalar()
        level_pool = conn.execute(text(f"SELECT COUNT(*) FROM {best_ranks_table}")).scalar()

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
        lottery_name=lottery_name,
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
    lottery_type = sys.argv[2] if len(sys.argv) > 2 else "p5"  # 默认排列5
    send_wechat_message(playtype_cn, lottery_type)
