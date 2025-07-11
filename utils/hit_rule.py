# utils/hit_rule.py
# 各彩票类型下的各个玩法的命中规则定义
import re

def match_hit(playtype: str, numbers: str, open_code: str, blue_code: str = "") -> bool:
    """
    命中判断（支持 福彩3D / 排列3 / 排列5 / 双色球 / 大乐透 / 快乐8）
    """
    nums = re.findall(r"\d+", numbers)
    open_nums = re.findall(r"\d+", open_code)

    nums_set = set(nums)
    open_set = set(open_nums)

    # ✅ 双色球专属判断（独立于大乐透）
    if playtype in [
        "红球独胆", "红球双胆", "红球三胆",
        "红球12码", "红球20码", "红球25码",
        "红球杀三", "红球杀六",
        "龙头两码", "凤尾两码",
        "蓝球定三", "蓝球定五", "蓝球杀五"
    ]:
        blue_nums = re.findall(r"\d+", blue_code) if blue_code else []
        blue_set = set(blue_nums)

        if playtype == "红球独胆":
            return len(nums_set & open_set) >= 1
        elif playtype == "红球双胆":
            return len(nums_set & open_set) >= 2
        elif playtype == "红球三胆":
            return len(nums_set & open_set) >= 3
        elif playtype in ["红球12码", "红球20码", "红球25码"]:
            return open_set.issubset(nums_set)  # 必须包含全部6个红球
        elif playtype in ["红球杀三", "红球杀六"]:
            return len(nums_set & open_set) == 0
        elif playtype in ["龙头两码", "凤尾两码"]:
            return len(nums_set & open_set) >= 2
        elif playtype in ["蓝球定三", "蓝球定五"]:
            return len(nums_set & blue_set) >= 1
        elif playtype == "蓝球杀五":
            return len(nums_set & blue_set) == 0

    # ✅ 快乐8命中判断（已更新）
    if playtype in [
        "1码", "2码", "3码", "4码", "5码", "6码", "7码", "8码", "9码", "10码", "12码", "15码"
    ]:
        required_hit = int(re.findall(r"\d+", playtype)[0])
        hit_count = len(nums_set & open_set)
        return hit_count >= required_hit
    elif playtype in ["杀5码", "杀8码", "杀10码"]:
        return len(nums_set & open_set) == 0  # 完全不能命中

    # ✅ 大乐透命中判断（保留原逻辑）
    if "红球" in playtype or "蓝球" in playtype or "杀蓝" in playtype:
        blue_nums = re.findall(r"\d+", blue_code) if blue_code else []
        if "蓝" in playtype:
            if "杀" in playtype:
                return len(set(nums) & set(blue_nums)) == 0
            elif "双" in playtype:
                return len(set(nums) & set(blue_nums)) >= 2
            else:
                return len(set(nums) & set(blue_nums)) >= 1
        else:
            if "杀" in playtype:
                return len(set(nums) & set(open_nums)) == 0
            else:
                return len(set(nums) & set(open_nums)) >= 1

    # ✅ 排列3/排列5/福彩3D命中判断（不改动）
    if len(open_nums) not in [3, 5]:
        return False

    hit_count = len(set(nums) & set(open_nums))
    unique_count = len(set(open_nums))
    is_group3 = unique_count == 2
    is_triplet = unique_count == 1

    if len(open_nums) == 5:
        position_map = {
            "万位": 0,
            "千位": 1,
            "百位": 2,
            "十位": 3,
            "个位": 4,
        }

        for pos_name, idx in position_map.items():
            if playtype.startswith(f"{pos_name}杀"):
                return str(open_nums[idx]) not in nums
            if playtype.startswith(f"{pos_name}定"):
                return str(open_nums[idx]) in nums

    if playtype == "杀一":
        return len(set(nums) & set(open_nums)) == 0
    elif playtype == "杀二":
        return len(set(nums) & set(open_nums)) == 0
    elif "独胆" in playtype:
        return hit_count >= 1
    elif "双胆" in playtype:
        return hit_count >= 2
    elif "三胆" in playtype or any(x in playtype for x in ["五码", "六码", "七码"]):
        if is_triplet:
            return open_nums[0] in nums
        elif is_group3:
            return hit_count >= 2
        else:
            return hit_count == 3
    elif "定位" in playtype and "-百位" in playtype:
        return len(set(nums) & {open_nums[0]}) >= 1
    elif "定位" in playtype and "-十位" in playtype:
        return len(set(nums) & {open_nums[1]}) >= 1
    elif "定位" in playtype and "-个位" in playtype:
        return len(set(nums) & {open_nums[2]}) >= 1
    elif playtype.startswith("百位定"):
        return len(set(nums) & {open_nums[0]}) >= 1
    elif playtype.startswith("十位定"):
        return len(set(nums) & {open_nums[1]}) >= 1
    elif playtype.startswith("个位定"):
        return len(set(nums) & {open_nums[2]}) >= 1

    return False
