# utils/db.py
# 整个项目的统一数据库连接、动态获取表名工具函数
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ✅ 仅在本地调试加载 .env，不影响 GitHub Actions 的环境变量注入
if os.getenv("GITHUB_ACTIONS") != "true":
    load_dotenv(override=False)


DB_CONFIG = {
    'host': os.getenv("MYSQL_HOST"),
    'port': int(os.getenv("MYSQL_PORT", 3306)),  # ✅ 加默认值
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'database': os.getenv("MYSQL_DATABASE"),
    'charset': 'utf8mb4',
}

PLAYTYPE_MAPPING_P5 = {
    "wanwei_sha3": "万位杀3",
    "wanwei_sha1": "万位杀1",
    "wanwei_ding5": "万位定5",
    "wanwei_ding3": "万位定3",
    "wanwei_ding1": "万位定1",
    "qianwei_sha3": "千位杀3",
    "qianwei_sha1": "千位杀1",
    "qianwei_ding5": "千位定5",
    "qianwei_ding3": "千位定3",
    "qianwei_ding1": "千位定1",
    "baiwei_sha3": "百位杀3",
    "baiwei_sha1": "百位杀1",
    "baiwei_ding5": "百位定5",
    "baiwei_ding3": "百位定3",
    "baiwei_ding1": "百位定1",
    "shiwei_sha3": "十位杀3",
    "shiwei_sha1": "十位杀1",
    "shiwei_ding5": "十位定5",
    "shiwei_ding3": "十位定3",
    "shiwei_ding1": "十位定1",
    "gewei_sha3": "个位杀3",
    "gewei_sha1": "个位杀1",
    "gewei_ding5": "个位定5",
    "gewei_ding3": "个位定3",
    "gewei_ding1": "个位定1",
}

PLAYTYPE_MAPPING_3D = {
    "danguan_1": "独胆",
    "shuangdan_2": "双胆",
    "sandan_3": "三胆",
    "wuma_zuxuan": "五码组选",
    "liuma_zuxuan": "六码组选",
    "qima_zuxuan": "七码组选",
    "sha1": "杀一",
    "sha2": "杀二",
    "baiwei_ding3": "百位定3",
    "shiwei_ding3": "十位定3",
    "gewei_ding3": "个位定3",
    "baiwei_ding1": "百位定1",
    "shiwei_ding1": "十位定1",
    "gewei_ding1": "个位定1",
    "ding_3x3x3_bai": "定位3*3*3-百位",
    "ding_3x3x3_shi": "定位3*3*3-十位",
    "ding_3x3x3_ge": "定位3*3*3-个位",
    "ding_4x4x4_bai": "定位4*4*4-百位",
    "ding_4x4x4_shi": "定位4*4*4-十位",
    "ding_4x4x4_ge": "定位4*4*4-个位",
    "ding_5x5x5_bai": "定位5*5*5-百位",
    "ding_5x5x5_shi": "定位5*5*5-十位",
    "ding_5x5x5_ge": "定位5*5*5-个位",
}


def get_engine():
    url = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4"
    return create_engine(url)

def get_prediction_table(lottery_name: str) -> str:
    mapping = {
        "福彩3D": "expert_predictions_3d",
        "排列3": "expert_predictions_p3",
        "排列5": "expert_predictions_p5",
        "快乐8": "expert_predictions_klb",
        "双色球": "expert_predictions_ssq",
        "大乐透": "expert_predictions_dlt",
    }
    return mapping.get(lottery_name, "expert_predictions_3d")

def get_result_table(lottery_name: str) -> str:
    mapping = {
        "福彩3D": "lottery_results_3d",
        "排列3": "lottery_results_p3",
        "排列5": "lottery_results_p5",
        "快乐8": "lottery_results_klb",
        "双色球": "lottery_results_ssq",
        "大乐透": "lottery_results_dlt",
    }
    return mapping.get(lottery_name, "lottery_results_p5")

def get_tasks_table(lottery_name: str) -> str:
    mapping = {
        "福彩3D": "tasks_3d",
        "排列5": "tasks_p5",
        "排列3": "tasks_p3",
    }
    return mapping.get(lottery_name, "tasks_p5")

def get_best_tasks_table(lottery_name: str) -> str:
    mapping = {
        "福彩3D": "best_tasks_3d",
        "排列5": "best_tasks_p5",
        "排列3": "best_tasks_p3",

    }
    return mapping.get(lottery_name, "best_tasks_p5")

def get_best_ranks_table(lottery_name: str) -> str:
    mapping = {
        "福彩3D": "best_ranks_3d",
        "排列5": "best_ranks_p5",
        "排列3": "best_ranks_p3",
    }
    return mapping.get(lottery_name, "best_ranks_p5")

def get_playtype_mapping(lottery_type: str) -> dict:
    mapping = {
        "p5": PLAYTYPE_MAPPING_P5,
        "3d": PLAYTYPE_MAPPING_3D,
    }
    return mapping.get(lottery_type.lower(), PLAYTYPE_MAPPING_P5)

LOTTERY_NAME_MAP = {
    "p5": "排列5",
    "3d": "福彩3D",
    "p3": "排列3",
    "klb": "快乐8",
    "ssq": "双色球",
    "dlt": "大乐透",
}

def get_lottery_name(lottery_type: str) -> str:
    return LOTTERY_NAME_MAP.get(lottery_type.lower(), "排列5")

def get_table_name(lottery_name: str, table_type: str) -> str:
    prefix_map = {
        "expert_predictions": get_prediction_table,
        "lottery_results": get_result_table,
        "tasks": get_tasks_table,
        "best_tasks": get_best_tasks_table,
        "best_ranks": get_best_ranks_table,
    }
    return prefix_map[table_type](lottery_name)
