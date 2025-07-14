# utils/config_loader.py
# 专门用于加载不同彩种的配置文件（如 config/p5_base.yaml、config/3d_base.yaml 等），让多个脚本统一、方便地读取配置内容。
import os
import yaml

def load_base_config(lottery_type: str) -> dict:
    """
    根据彩种类型（如 'p5', '3d'）加载对应的配置文件（如 config/p5_base.yaml）
    """
    config_path = os.path.join("config", f"{lottery_type.lower()}_base.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"未找到配置文件：{config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
