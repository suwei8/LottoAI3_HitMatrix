import os
import re

TABLES = {
    "tasks_p5": [
        "id", "position", "lookback_n", "lookback_offset",
        "query_playtype_name", "analyze_playtype_name",
        "hit_rank_list", "enable", "skip_if_few",
        "resolve_tie_mode", "reverse_on_tie", "status",
        "total_issues", "hit_count", "skip_count", "hit_rate",
        "created_at", "updated_at"
    ],
    "best_tasks_p5": [
        "id", "position", "playtype", "lookback_n", "lookback_offset",
        "hit_rank_list", "enable", "skip_if_few",
        "resolve_tie_mode", "reverse_on_tie", "hit_rate", "created_at"
    ],
    "best_ranks_p5": [
        "id", "playtype", "position", "lookback_n",
        "hit_rank_list", "enable", "total_issues",
        "open_rank_counter", "unhit_ranks", "created_at"
    ]
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_SQL = os.path.join(DATA_DIR, "merged_tasks_p5.sql")
def extract_rows(sql_text: str, table_name: str):
    rows = []
    # 兼容 INSERT INTO ... (cols) VALUES (...) 多段形式
    insert_pattern = re.compile(
        rf"INSERT INTO\s+`?{table_name}`?\s*(\([^)]*\))?\s*VALUES\s*(.*?);",
        re.IGNORECASE | re.DOTALL
    )

    for match in insert_pattern.finditer(sql_text):
        _, values_block = match.groups()
        value_groups = re.findall(r"\(([^;]*?)\)(?:,|\s*;)\s*", values_block, re.DOTALL)
        for group in value_groups:
            values = [v.strip() for v in group.split(",")]
            if len(values) >= 2:
                rows.append(values[1:])  # 去除 id
    return rows

def merge_sql_files_with_auto_id(filepaths: list, start_ids: dict):
    all_data = {table: [] for table in TABLES}

    for path in filepaths:
        print(f"\n📂 正在读取: {path}")
        with open(path, encoding="utf-8") as f:
            print(f"📄 正在打开文件: {path}")
            sql_text = f.read()
        for table in TABLES:
            rows = extract_rows(sql_text, table)
            all_data[table].extend(rows)
            print(f"✅ 表 {table} 提取 {len(rows)} 条记录")

    with open(OUTPUT_SQL, "w", encoding="utf-8") as f:
        for table, columns in TABLES.items():
            all_rows = all_data[table]
            if not all_rows:
                continue
            print(f"\n🔗 合并表 {table} 总数: {len(all_rows)} 条")
            col_names = ", ".join(columns)
            merged_sql = f"INSERT INTO {table} ({col_names}) VALUES\n"
            lines = []
            for idx, row in enumerate(all_rows, start=start_ids.get(table, 1)):
                lines.append(f"({idx}," + ",".join(row) + ")")
            merged_sql += ",\n".join(lines) + ";\n"
            f.write(f"\n-- 合并数据：{table} --\n")
            f.write(merged_sql)
    print(f"\n🎉 所有表合并完成 ➜ {OUTPUT_SQL}")

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        print(f"❌ 未找到目录: {DATA_DIR}")
        exit(1)

    sql_files = [
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.endswith(".sql")
    ]

    if not sql_files:
        print("❌ 当前目录无 .sql 文件")
    else:
        start_ids = {
            "tasks_p5": 1001,
            "best_tasks_p5": 501,
            "best_ranks_p5": 501,
        }
        merge_sql_files_with_auto_id(sql_files, start_ids)
