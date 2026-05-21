#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox M3U直播源获取工具（Cloudflare绕过版）
优化版：取消所有原有分组，统一放在mengyxx分组下
"""
import re
import time

try:
    import cloudscraper
except ImportError:
    print("安装 cloudscraper: pip install cloudscraper")
    exit(1)

# ==================== 配置 ====================
API_URLS = [
    "https://ds65.tv1288.xyz",
]
EXCLUDE_KEYWORDS = ["音乐", "金曲", "DJ", "黄色", "激情", "私拍", "体育", "代理", "咪"]
OUTPUT_FILE = "my3.txt"
MAX_RETRIES = 3
FIXED_GROUP = "mengyxx,#genre#"  # 固定分组名称


def create_scraper():
    """创建Cloudflare绕过的scraper"""
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },
        delay=10
    )


def fetch_m3u(url):
    scraper = create_scraper()
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  尝试 {attempt + 1}/{MAX_RETRIES}...")
            resp = scraper.get(url, timeout=30)
            text = resp.text.strip()
            
            if "Just a moment" in text or "cloudflare" in text.lower():
                print(f"  ⚠ 仍被Cloudflare拦截，尝试更换指纹...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)
                    scraper = create_scraper()
                    continue
            
            if text.startswith("#EXTM3U") or "#EXTINF" in text[:500]:
                print(f"  ✓ 成功获取 (大小: {len(text)} 字节)")
                return text
            else:
                print(f"  前100字符: {text[:100]}")
                return text
                
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(3)
                continue
            return None
    
    return None


def parse_m3u_to_txt(m3u_content):
    """将M3U转换为TXT格式（不保留原始分组）"""
    if not m3u_content:
        return ""
    
    lines = m3u_content.splitlines()
    result = []
    current_name = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 跳过全局注释和分组
        if line.startswith("#EXTM3U") or line.startswith("#EXT-X-") or line.startswith("//"):
            continue
        
        # 处理 #EXTINF 行
        if line.startswith("#EXTINF"):
            # 只提取频道名，忽略分组信息
            match = re.search(r',([^,]+)$', line)
            if match:
                current_name = match.group(1).strip()
            continue
        
        # 处理 URL 行 - 不添加任何分组标记
        if line and not line.startswith("#") and current_name:
            result.append(f"{current_name},{line}")
            current_name = None
    
    return "\n".join(result)


def filter_by_group_and_keyword(txt_content, exclude_keywords):
    """按关键词过滤（频道名和URL中含有关键词也过滤）"""
    if not txt_content:
        return ""
    
    lines = txt_content.splitlines()
    filtered = []
    skipped_count = 0
    
    for line in lines:
        # 跳过所有原有的#genre#行
        if line.endswith(",#genre#"):
            continue
        
        # 检查是否包含排除关键词
        if any(kw.lower() in line.lower() for kw in exclude_keywords):
            skipped_count += 1
            continue
        
        filtered.append(line)
    
    if skipped_count > 0:
        print(f"  已过滤 {skipped_count} 个含排除关键词的频道")
    
    return "\n".join(filtered)


def main():
    print("=" * 50)
    print("TVBox M3U → TXT 转换工具 (Cloudflare绕过版)")
    print("=" * 50)
    
    all_txt_parts = []
    
    for url in API_URLS:
        print(f"\n正在处理: {url}")
        m3u = fetch_m3u(url)
        
        if not m3u:
            print("  ✗ 获取失败，跳过")
            continue
        
        print("  ↳ 转换为 TXT 格式...")
        txt = parse_m3u_to_txt(m3u)
        
        if txt:
            all_txt_parts.append(txt)
            print(f"  ↳ 转换完成，共 {len(txt.splitlines())} 行")
        else:
            print("  ↳ 转换结果为空")
    
    if not all_txt_parts:
        print("\n❌ 未获取到任何有效内容，退出")
        return
    
    combined = "\n".join(all_txt_parts)
    filtered = filter_by_group_and_keyword(combined, EXCLUDE_KEYWORDS)
    
    # 去重
    lines = filtered.splitlines()
    unique_lines = list(dict.fromkeys(lines))  # 保持顺序去重
    dedup_count = len(lines) - len(unique_lines)
    
    if dedup_count > 0:
        print(f"  已去除 {dedup_count} 个重复频道")
    
    # 添加固定分组在第一行
    final_content = FIXED_GROUP + "\n" + "\n".join(unique_lines)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print("\n" + "=" * 50)
    print(f"✅ 完成！已保存到 {OUTPUT_FILE}")
    print(f"  原始频道数: {len(combined.splitlines())}")
    print(f"  最终频道数: {len(unique_lines)}")
    print(f"  文件大小: {len(final_content.encode('utf-8'))} 字节")
    print(f"  固定分组: {FIXED_GROUP}")
    print("=" * 50)
    
    # 显示前几行预览
    print("\n📄 内容预览（前10行）：")
    preview_lines = final_content.splitlines()[:10]
    for i, line in enumerate(preview_lines, 1):
        print(f"  {i:2d}. {line[:80]}")


if __name__ == "__main__":
    main()
