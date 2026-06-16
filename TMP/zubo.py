#!/usr/bin/env python3
"""
IPTV直播源下载与分组过滤工具
- 从指定URL列表读取M3U内容
- 过滤掉组名包含指定关键词的整个分组
- 保存结果到指定文件
"""

import requests
import re
import os
import sys

# ============ 配置区 ============
URLS = [
    "https://raw.githubusercontent.com/q1017673817/iptvz/refs/heads/main/zubo_all.txt",
]

OUTPUT_FILE = "TMP/zubo.txt"

# 需要过滤掉的关键词列表（组名包含这些词的整个分组都会被移除）
FILTER_KEYWORDS = ["联通", "移动"]

# 请求超时（秒）
TIMEOUT = 30

# 请求头
HEADERS = {
    "User-Agent": "okhttp/3.12.1"
}
# ================================


def fetch_url(url: str) -> str:
    """从URL获取文本内容"""
    print(f"正在下载: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        print(f"  下载成功，大小: {len(resp.text)} 字符")
        return resp.text
    except requests.RequestException as e:
        print(f"  下载失败: {e}")
        return ""


def parse_and_filter(content: str, filter_keywords: list) -> tuple:
    """
    解析M3U内容并按分组过滤
    返回: (过滤后的内容, 统计信息dict)
    """
    lines = content.splitlines()

    # 按 #genre# 分组标签切分
    # 格式: 频道名,#genre#组名
    groups = {}          # 组名 -> [行列表]
    current_group = None # 当前组名
    header_lines = []    # 文件头部（第一组之前的行）

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测分组标签
        if ",#genre#" in line:
            # 提取组名
            parts = line.split(",#genre#", 1)
            current_group = parts[1].strip() if len(parts) > 1 else "未分组"
            if current_group not in groups:
                groups[current_group] = []
            groups[current_group].append(line)
        else:
            if current_group is not None:
                groups[current_group].append(line)
            else:
                # 第一组之前的行（如可能的M3U头）
                header_lines.append(line)

    # 统计
    stats = {
        "total_groups": len(groups),
        "total_channels": sum(len(channels) - 1 for channels in groups.values()),
        "filtered_groups": [],
        "filtered_channels": 0,
    }

    # 过滤
    filtered_groups = {}
    for group_name, channels in groups.items():
        if any(kw in group_name for kw in filter_keywords):
            stats["filtered_groups"].append(group_name)
            stats["filtered_channels"] += len(channels) - 1
            continue
        filtered_groups[group_name] = channels

    stats["kept_groups"] = len(filtered_groups)
    stats["kept_channels"] = sum(len(channels) - 1 for channels in filtered_groups.values())

    # 拼接结果
    result_lines = []
    for line in header_lines:
        result_lines.append(line)

    for group_name, channels in filtered_groups.items():
        for line in channels:
            result_lines.append(line)

    return "\n".join(result_lines), stats


def main():
    # 如果命令行传了参数，覆盖默认配置
    urls = sys.argv[1:] if len(sys.argv) > 1 else URLS
    filter_keywords = FILTER_KEYWORDS
    output_file = OUTPUT_FILE

    print("=" * 50)
    print("IPTV直播源下载与分组过滤工具")
    print("=" * 50)
    print(f"下载源: {len(urls)} 个URL")
    print(f"过滤关键词: {filter_keywords}")
    print(f"输出文件: {output_file}")
    print()

    # 下载所有URL内容
    all_content = []
    for url in urls:
        content = fetch_url(url)
        if content:
            all_content.append(content)

    if not all_content:
        print("所有URL下载失败，程序退出")
        sys.exit(1)

    # 合并内容
    merged = "\n".join(all_content)
    print(f"\n合并后总大小: {len(merged)} 字符")

    # 解析并过滤
    result, stats = parse_and_filter(merged, filter_keywords)

    # 打印统计
    print(f"\n--- 过滤统计 ---")
    print(f"原始分组数: {stats['total_groups']}")
    print(f"原始频道数: {stats['total_channels']}")
    print(f"过滤掉的分组: {stats['filtered_groups']}")
    print(f"过滤掉的频道数: {stats['filtered_channels']}")
    print(f"保留分组数: {stats['kept_groups']}")
    print(f"保留频道数: {stats['kept_channels']}")

    # 保存结果
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"\n结果已保存到: {output_file} ({len(result)} 字符)")


if __name__ == "__main__":
    main()
