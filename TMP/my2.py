#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox直播接口解密工具
"""

import requests
import json
import re
from urllib.parse import unquote

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 全局配置 ====================

# 目标接口地址列表
API_URLS = [
    "https://ds65.tv1288.xyz",
]

# 排除关键词列表
EXCLUDE_KEYWORDS = [
    "音乐", "金曲", "DJ", "黄色", "激情", "私拍",
]

# 输出文件名
OUTPUT_FILE = "my3.txt"


class TVBoxAPI:
    """TVBox API 解密器"""

    def __init__(self):
        self.user_agents = [
            'okhttp/3.12.1',
            'okhttp/4.9.0',
            'Dalvik/2.1.0 (Linux; U; Android 12; SM-G998B Build/SP1A.210812.016)',
            'TVBox',
            'Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36',
        ]
        self.session = requests.Session()
        self.session.verify = False
        self.data = None

    def fetch_api(self, url, params=None):
        """获取API数据，尝试多种User-Agent"""
        for ua in self.user_agents:
            headers = {
                'User-Agent': ua,
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            try:
                print(f"  尝试 User-Agent: {ua[:30]}...")
                response = self.session.get(url, headers=headers, params=params, timeout=15, allow_redirects=True)
                response.encoding = 'utf-8'
                text = response.text.strip()
                
                # 检查是否是JSON格式
                if text and (text.startswith('{') or text.startswith('[')):
                    print(f"  成功获取数据，长度: {len(text)} 字节")
                    return text
                
                # 打印前200字符看看是什么
                print(f"  返回内容前200字符: {text[:200]}")
                
            except requests.RequestException as e:
                print(f"  请求失败: {e}")
                continue
        
        return None

    def fetch_live_content(self, url):
        """获取直播源内容"""
        for ua in self.user_agents[:2]:  # 只试前两个UA
            headers = {
                'User-Agent': ua,
                'Accept': '*/*',
            }
            try:
                response = self.session.get(url, headers=headers, timeout=60)
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'utf-16']:
                    try:
                        response.encoding = encoding
                        content = response.text
                        if '频道' in content or '#genre#' in content or '#EXTM3U' in content or ',' in content[:500]:
                            return content
                    except:
                        continue
                response.encoding = 'utf-8'
                return response.text
            except requests.RequestException as e:
                continue
        return None

    def parse_json(self, text):
        """解析JSON数据"""
        if not text:
            return False
        
        text = text.strip()
        
        # 移除BOM头
        if text.startswith('\ufeff'):
            text = text[1:]
        
        # 移除JavaScript风格的注释
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            if '//' in line and not line.strip().startswith('"'):
                in_string = False
                result = []
                for i, char in enumerate(line):
                    if char == '"' and (i == 0 or line[i-1] != '\\'):
                        in_string = not in_string
                    if char == '/' and i < len(line) - 1 and line[i+1] == '/' and not in_string:
                        break
                    result.append(char)
                cleaned_lines.append(''.join(result).rstrip())
            else:
                cleaned_lines.append(line.rstrip())

        text = '\n'.join(cleaned_lines)

        try:
            self.data = json.loads(text)
            return True
        except json.JSONDecodeError as e:
            print(f"  JSON解析失败: {e}")
            print(f"  出错位置附近: {text[max(0, e.pos-50):e.pos+50] if hasattr(e, 'pos') else text[:100]}")
            return False

    def get_live_sources(self):
        """获取直播源地址列表"""
        if not self.data:
            return []
        lives = self.data.get('lives', [])
        sources = []
        for live in lives:
            sources.append({
                '名称': live.get('name', '未知'),
                '地址': live.get('url', ''),
            })
        return sources


def filter_live_content(content, exclude_keywords):
    """过滤直播源内容"""
    if not content:
        return ""

    lines = content.split('\n')
    filtered_lines = []
    skip_mode = False

    for line in lines:
        line_stripped = line.strip()

        if '#genre#' in line_stripped:
            should_skip = False
            for keyword in exclude_keywords:
                if keyword.lower() in line_stripped.lower():
                    should_skip = True
                    break
            skip_mode = should_skip
        else:
            if not skip_mode:
                if line_stripped and ',' in line_stripped:
                    filtered_lines.append(line)

    result = ["gt,#genre#"]
    result.extend(filtered_lines)
    return '\n'.join(result)


def parse_m3u_to_txt(content):
    """将M3U格式转换为TXT格式"""
    if not content:
        return ""

    lines = content.split('\n')
    result = []
    current_channel = None

    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            match = re.search(r',(.+)$', line)
            if match:
                current_channel = match.group(1).strip()
            group_match = re.search(r'group-title="([^"]*)"', line)
            if group_match:
                group = group_match.group(1)
                result.append(f"{group},#genre#")
        elif line and not line.startswith('#'):
            if current_channel:
                result.append(f"{current_channel},{line}")
                current_channel = None

    return '\n'.join(result)


def main():
    """主函数"""
    print("TVBox直播接口解密工具")

    all_live_content = []

    for api_index, api_url in enumerate(API_URLS, 1):
        print(f"\n正在处理接口 {api_index}: {api_url}")

        api = TVBoxAPI()

        text = api.fetch_api(api_url)
        if not text:
            print("  获取数据失败，跳过此接口")
            continue

        if not api.parse_json(text):
            print("  JSON解析失败，跳过此接口")
            continue

        live_sources = api.get_live_sources()
        print(f"  找到 {len(live_sources)} 个直播源")
        
        for source in live_sources:
            name = source.get('名称', '未知')
            url = source.get('地址', '')
            if not url:
                continue

            print(f"  正在获取直播源: {name}")
            content = api.fetch_live_content(url)
            if content:
                if content.strip().startswith('#EXTM3U'):
                    content = parse_m3u_to_txt(content)
                all_live_content.append(content)
                print(f"    获取成功，长度: {len(content)} 字节")

    combined_content = '\n\n'.join(all_live_content)

    filtered_content = filter_live_content(combined_content, EXCLUDE_KEYWORDS)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(filtered_content)

    print(f"\n处理完成！已保存到 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
