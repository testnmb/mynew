import re
import os
import sys
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# 全局排除关键词定义（用于分类排除）
EXCLUDE_KEYWORDS = ["移动", "联通", "私密", "少儿", "体育", "记录", "听书", "老年", "解说", 
                     "监控", "DJ", "加入", "(内)", "韩剧", "专用", "动漫", "非诚", "向前冲", 
                     "百分百", "集结号", "好野", "行不行", "更新", "国际影院"]

# 新增：行内容过滤关键词（只要行中包含任意一个关键词，该行即被过滤）
CONTENT_FILTER_KEYWORDS = ["ottiptv", "盗源", "DJ", "P2p", "shorturl", "更新", "group"]

# 请根据实际需求修改


class TVSourceProcessor:
    def __init__(self):
        self.all_lines = []
        
        # 配置 Chrome 无头模式
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def fetch_url_content(self, url: str):
        """使用 Selenium 获取URL内容"""
        try:
            print(f"获取: {url}")
            self.driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            
            # 获取页面内容
            content = self.driver.find_element(By.TAG_NAME, "pre").text
            
            # 清理并分割行
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            print(f"  成功: {len(lines)} 行")
            return lines
        except Exception as e:
            print(f"  失败: {e}")
            return []
    
    def fetch_multiple_urls(self, urls: list):
        """获取多个URL内容"""
        self.all_lines = []
        for url in urls:
            lines = self.fetch_url_content(url)
            if lines:
                self.all_lines.extend(lines)
        print(f"总计: {len(self.all_lines)} 行")
        return len(self.all_lines) > 0
    
    def remove_excluded_sections(self):
        """排除指定区域"""
        if not self.all_lines:
            return []
        
        result = []
        in_excluded_section = False
        
        for line in self.all_lines:
            if "#genre#" in line:
                if any(keyword in line for keyword in EXCLUDE_KEYWORDS):
                    in_excluded_section = True
                else:
                    in_excluded_section = False
                    result.append(line)
            elif not in_excluded_section:
                result.append(line)
        
        print(f"排除后: {len(result)} 行")
        return result
    
    def is_valid_base64(self, s: str) -> bool:
        """
        检查字符串是否为有效的 base-64 编码
        
        Args:
            s: 要检查的字符串
            
        Returns:
            bool: True 表示是有效的 base-64，False 表示无效
        """
        s = s.strip()
        
        # 空字符串或太短
        if len(s) < 1:
            return False
        
        # 只包含 base-64 字符（A-Z, a-z, 0-9, +, /, =）
        base64_pattern = re.compile(r'^[A-Za-z0-9+/=]+$')
        if not base64_pattern.match(s):
            return False
        
        # 长度必须是 4 的倍数
        if len(s) % 4 != 0:
            return False
        
        # 检查填充字符 = 的数量（最多 2 个）
        pad_count = s.count('=')
        if pad_count > 2:
            return False
        
        # 填充字符必须在末尾
        if '=' in s and not s.endswith('=') and not s.endswith('=='):
            return False
        
        # 尝试解码验证
        try:
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False
    
    def check_base64_in_line(self, line: str) -> tuple:
        """
        检查行中是否包含无效的 base-64 编码
        
        Args:
            line: 要检查的行内容
            
        Returns:
            tuple: (has_bad_base64, reason)
                   has_bad_base64: True 表示包含无效 base-64
                   reason: 错误原因描述
        """
        # 提取 URL
        url_match = re.search(r'https?://[^\s,]+', line)
        if not url_match:
            return (False, "")
        
        url = url_match.group(0)
        
        # 检查 URL 参数中的 base-64 字符串
        # 匹配参数值：= 后面的值（可能是 base-64）
        param_matches = re.findall(r'[?&]([a-zA-Z_]+)=([A-Za-z0-9+/=]{16,})', url)
        
        for param_name, param_value in param_matches:
            # 跳过明显不是 base-64 的参数（如纯数字）
            if re.match(r'^\d+$', param_value):
                continue
            
            # 检查是否是有效的 base-64
            if not self.is_valid_base64(param_value):
                return (True, f"参数 {param_name} 无效: 长度={len(param_value)}, 值={param_value[:50]}...")
        
        # 检查 URL 路径中的长字符串（可能是 base-64）
        # 匹配路径段中长度 >= 32 且只包含 base-64 字符的字符串
        path_without_domain = re.sub(r'^https?://[^/]+', '', url)
        path_segments = re.findall(r'/([A-Za-z0-9+/=]{32,})', path_without_domain)
        
        for path_segment in path_segments:
            if not self.is_valid_base64(path_segment):
                return (True, f"路径段无效: 长度={len(path_segment)}, 值={path_segment[:50]}...")
        
        return (False, "")
    
    def remove_genre_lines_and_deduplicate(self, lines: list):
        """
        删除genre行，并按URL去重。
        同时根据 CONTENT_FILTER_KEYWORDS 过滤掉包含指定关键词的行。
        新增：过滤掉包含无效 base-64 编码的行。
        """
        result = []
        seen_urls = set()
        
        filtered_count = 0
        bad_base64_count = 0
        
        for line in lines:
            # 跳过 genre 行
            if "#genre#" in line:
                continue
            
            # 跳过空行
            if not line.strip():
                continue
            
            # 内容过滤（不区分大小写）
            line_lower = line.lower()
            if any(keyword.lower() in line_lower for keyword in CONTENT_FILTER_KEYWORDS):
                filtered_count += 1
                continue  # 过滤掉该行
            
            # 新增：检查是否包含无效的 base-64 编码
            has_bad_base64, bad_reason = self.check_base64_in_line(line)
            if has_bad_base64:
                bad_base64_count += 1
                if bad_base64_count <= 10:  # 只打印前10个
                    print(f"  过滤 bad base-64: {line[:80]}...")
                    print(f"    原因: {bad_reason}")
                continue
            
            # 提取URL去重
            url_match = re.search(r'(https?://[^\s,]+)', line)
            if url_match:
                url = url_match.group(1)
                if url not in seen_urls:
                    seen_urls.add(url)
                    result.append(line)
            else:
                result.append(line)
        
        print(f"内容过滤: {filtered_count} 行被过滤")
        print(f"Bad base-64 过滤: {bad_base64_count} 行被过滤")
        if bad_base64_count > 10:
            print(f"  (仅显示前10个错误详情)")
        print(f"去重后: {len(result)} 行")
        
        return result
    
    def save_to_file(self, lines: list, filename: str, first_line: str):
        """保存到文件"""
        try:
            content = [first_line] + lines
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            file_size = os.path.getsize(filename)
            print(f"保存: {filename} ({len(content)}行, {file_size}字节)")
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False
    
    def process(self):
        """主处理流程"""
        print("开始处理直播源")
        
        # 只使用指定的URL
        urls = [
            "https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg1",
            "https://raw.githubusercontent.com/fafa002/yf2025/refs/heads/main/yiyifafa.txt",
            "https://raw.githubusercontent.com/zxmlxw520/5566/refs/heads/main/cjdszb.txt",
        ]
        
        print(f"源URL: {len(urls)}个")
        
        # 1. 获取内容
        if not self.fetch_multiple_urls(urls):
            print("无内容可处理")
            self.driver.quit()
            return False
        
        # 2. 排除处理
        filtered = self.remove_excluded_sections()
        if not filtered:
            print("排除后无内容")
            self.driver.quit()
            return False
        
        # 3. 去重及内容过滤处理（新增 bad base-64 过滤）
        final = self.remove_genre_lines_and_deduplicate(filtered)
        if not final:
            print("去重后无内容")
            self.driver.quit()
            return False
        
        # 4. 保存文件
        if self.save_to_file(final, "ttest.txt", "test,#genre#"):
            print("处理完成")
            self.driver.quit()
            return True
        else:
            self.driver.quit()
            return False


def main():
    """主函数"""
    processor = TVSourceProcessor()
    success = processor.process()
    
    # 退出状态码
    if success and os.path.exists("ttest.txt"):
        print(f"文件位置: {os.path.abspath('ttest.txt')}")
        sys.exit(0)
    else:
        print("处理失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
