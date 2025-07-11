# utils/logger.py
# 日志打印工具函数
import sys
import os
from datetime import datetime

_log_buffer = []
_current_log_file_path = None

def log(*args, sep=" ", end="\n", **kwargs):
    msg = sep.join(map(str, args)) + end
    sys.stdout.write(msg)
    sys.stdout.flush()
    _log_buffer.append(msg)

def init_log_capture(script_name_hint=None, lottery_name=None):
    global _current_log_file_path
    if script_name_hint is None:
        script_name_hint = "unnamed_script"

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_dir = os.path.join(project_root, "log")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 🚩 如果外面传了 lottery_name，就用它优先；否则用 script 名
    if lottery_name:
        lottery_pinyin = lottery_name.lower()
        if "排列3" in lottery_name or "p3" in lottery_name:
            lottery_pinyin = "p3"
        elif "排列5" in lottery_name or "p5" in lottery_name:
            lottery_pinyin = "p5"
        elif "福彩3D" in lottery_name or "3d" in lottery_name:
            lottery_pinyin = "3d"
        elif "快乐8" in lottery_name or "kl8" in lottery_name:
            lottery_pinyin = "kl8"
        base_name = f"run_{lottery_pinyin}_{os.path.splitext(script_name_hint)[0]}"
    else:
        base_name = os.path.splitext(script_name_hint)[0]


    _current_log_file_path = os.path.join(log_dir, f"{base_name}_{timestamp}.log")

    _log_buffer.clear()
    sys.stdout.write(
        f"📁 当前脚本路径: scripts/{script_name_hint}，Run #{os.getenv('GITHUB_RUN_NUMBER', '')}\n"
    )
    sys.stdout.flush()

def save_log_file_if_needed(log_save_mode):
    if not log_save_mode or not _log_buffer or not _current_log_file_path:
        return
    try:
        with open(_current_log_file_path, "w", encoding="utf-8") as f:
            f.writelines(_log_buffer)
        sys.stdout.write(f"📄 日志已保存至: {_current_log_file_path}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"❌ 日志保存失败: {e}\n")
        sys.stdout.flush()
