import os, sys
from utils.report_tools import generate_wechat_message
import requests
from sqlalchemy import text
from utils.db import get_engine

playtype_cn = sys.argv[1] if len(sys.argv) > 1 else "未指定玩法"
run_number = os.getenv("GITHUB_RUN_NUMBER", "DEV")
mins = os.getenv("DURATION_MINUTES", "0")
secs = os.getenv("DURATION_SECONDS", "0")

print(f"耗时分钟: {mins}，耗时秒: {secs}")

# === 这里查数据库、生成内容 ===
engine = get_engine()
with engine.connect() as conn:
    min_max = conn.execute(text("SELECT MIN(issue_name), MAX(issue_name) FROM lottery_results_p5")).fetchone()
    issue_start = min_max[1]
    issue_end = min_max[0]
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
    secs=secs
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
