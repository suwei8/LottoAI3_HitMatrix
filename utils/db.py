# utils/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_CONFIG = {
    'host': os.getenv("MYSQL_HOST"),
    'port': int(os.getenv("MYSQL_PORT")),
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'database': os.getenv("MYSQL_DATABASE"),
    'charset': 'utf8mb4',
}

PLAYTYPE_MAPPING = {
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
    return mapping.get(lottery_name, "lottery_results_3d")
