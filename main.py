import requests
import re
import os
from typing import List, Set

# 全局排除关键词定义
EXCLUDE_KEYWORDS = ["成人", "激情", "情色", "涩情", "18禁", "R18"]

class TVSourceProcessor:
    def __init__(self):
        """
        初始化处理器
        """
        self.all_lines = []
    
    def fetch_url_content(self, url: str) -> List[str]:
        """
        从URL获取文件内容
        :param url: 文件URL
        :return: 文件内容行列表
        """
        try:
            print(f"正在获取: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 根据响应编码处理文本
            if response.encoding:
                content = response.text
            else:
                content = response.content.decode('utf-8', errors='ignore')
            
            lines = content.splitlines()
            print(f"从 {url} 获取了 {len(lines)} 行内容")
            return lines
            
        except requests.exceptions.RequestException as e:
            print(f"获取 {url} 失败: {e}")
            return []
        except Exception as e:
            print(f"处理 {url} 时出错: {e}")
            return []
    
    def fetch_multiple_urls(self, urls: List[str]) -> None:
        """
        从多个URL获取内容并合并
        :param urls: URL列表
        """
        self.all_lines = []
        for url in urls:
            lines = self.fetch_url_content(url)
            self.all_lines.extend(lines)
        
        print(f"总共获取了 {len(self.all_lines)} 行内容")
    
    def remove_excluded_sections(self) -> List[str]:
        """
        根据全局排除关键词移除相关区域
        :return: 处理后的行列表
        """
        if not self.all_lines:
            return []
        
        result = []
        in_excluded_section = False
        
        for line in self.all_lines:
            # 检查是否为genre行
            if "#genre#" in line:
                # 检查当前genre行是否包含排除关键词
                contains_exclude = any(keyword in line for keyword in EXCLUDE_KEYWORDS)
                
                if contains_exclude:
                    # 开始排除区域
                    in_excluded_section = True
                    print(f"发现排除区域: {line[:50]}...")
                else:
                    # 结束排除区域或不在排除区域
                    in_excluded_section = False
                    result.append(line)
            else:
                # 如果不是genre行
                if not in_excluded_section:
                    result.append(line)
                # 如果在排除区域内，跳过该行
        
        print(f"排除处理后剩余 {len(result)} 行内容")
        return result
    
    def remove_genre_lines_and_deduplicate(self, lines: List[str]) -> List[str]:
        """
        删除所有genre行并去重
        :param lines: 输入行列表
        :return: 处理后的行列表
        """
        result = []
        seen_urls: Set[str] = set()
        
        for line in lines:
            # 跳过所有包含#genre#的行
            if "#genre#" in line:
                continue
            
            # 跳过空行
            if not line.strip():
                continue
            
            # 尝试提取URL部分
            url_part = self.extract_url_from_line(line)
            
            if url_part:
                # 如果是URL行，检查是否重复
                if url_part not in seen_urls:
                    seen_urls.add(url_part)
                    result.append(line)
            else:
                # 如果不是URL行，直接添加
                result.append(line)
        
        print(f"去重后剩余 {len(result)} 行内容")
        return result
    
    def extract_url_from_line(self, line: str) -> str:
        """
        从行中提取URL
        :param line: 输入行
        :return: 提取的URL或空字符串
        """
        # 尝试找到http或https开头的URL
        urls = re.findall(r'https?://[^\s,]+', line)
        if urls:
            return urls[0]
        
        # 如果没有找到完整URL，尝试提取逗号分隔的URL部分
        parts = line.split(',')
        if len(parts) > 1 and ('http://' in parts[1] or 'https://' in parts[1]):
            return parts[1].strip()
        
        return ""
    
    def save_to_file(self, lines: List[str], filename: str = "my1.txt", first_line: str = "smt,#genre#") -> None:
        """
        保存处理结果到文件
        :param lines: 要保存的行列表
        :param filename: 输出文件名
        :param first_line: 文件第一行内容
        """
        try:
            # 准备要写入的内容
            content_to_write = []
            
            # 添加第一行
            if first_line:
                content_to_write.append(first_line)
            
            # 添加其他行
            content_to_write.extend(lines)
            
            # 写入文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_to_write))
            
            print(f"成功保存到 {filename}，共 {len(content_to_write)} 行")
            print(f"文件大小: {os.path.getsize(filename)} 字节")
            
        except Exception as e:
            print(f"保存文件时出错: {e}")
    
    def process(self, urls: List[str], output_file: str = "my1.txt", first_line: str = "smt,#genre#") -> None:
        """
        完整处理流程
        :param urls: 要处理的URL列表
        :param output_file: 输出文件名
        :param first_line: 文件第一行内容
        """
        print("=" * 50)
        print(f"TV直播源批量处理工具")
        print(f"排除关键词: {EXCLUDE_KEYWORDS}")
        print("=" * 50)
        
        # 1. 从多个URL获取内容
        self.fetch_multiple_urls(urls)
        
        if not self.all_lines:
            print("没有获取到任何内容，程序退出")
            return
        
        # 2. 排除不需要的区域
        filtered_lines = self.remove_excluded_sections()
        
        if not filtered_lines:
            print("排除处理后没有剩余内容，程序退出")
            return
        
        # 3. 保存中间处理结果
        debug_file = output_file.replace(".txt", "_debug.txt")
        self.save_to_file(filtered_lines, debug_file, first_line)
        print(f"中间文件已保存: {debug_file}")
        
        # 4. 删除genre行并去重
        final_lines = self.remove_genre_lines_and_deduplicate(filtered_lines)
        
        # 5. 保存最终结果
        self.save_to_file(final_lines, output_file, first_line)
        
        print("=" * 50)
        print("批量处理完成！")
        print("=" * 50)


def main():
    """
    主函数：批量处理模式
    """
    print("TV直播源批量处理工具")
    print("-" * 50)
    
    # 从用户输入获取URL列表
    urls = [
         "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/斯瑪特直播源1",
        "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/斯瑪特直播源2",
    ]
    count = 1
    while True:
        url = input(f"URL {count}: ").strip()
        if not url:
            if count == 1:
                print("至少需要输入一个URL")
                continue
            break
        urls.append(url)
        count += 1
    
    # 显示要处理的URL
    print(f"\n将要处理 {len(urls)} 个URL:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    # 获取输出文件名
    default_output = "my1.txt"
    output_file = input(f"\n输出文件名（默认: {default_output}）: ").strip()
    if not output_file:
        output_file = default_output
    
    # 获取第一行内容
    custom_first_line = input(f"文件第一行内容（默认: smt,#genre#）: ").strip()
    if not custom_first_line:
        custom_first_line = "smt,#genre#"
    
    # 确认处理
    print(f"\n配置信息:")
    print(f"  URL数量: {len(urls)}")
    print(f"  输出文件: {output_file}")
    print(f"  第一行内容: {custom_first_line}")
    print(f"  排除关键词: {EXCLUDE_KEYWORDS}")
    
    confirm = input("\n是否开始处理？(y/n): ").strip().lower()
    if confirm != 'y':
        print("用户取消操作")
        return
    
    # 创建处理器并执行
    processor = TVSourceProcessor()
    processor.process(urls, output_file, custom_first_line)


if __name__ == "__main__":
    # 直接运行批量处理
    main()
