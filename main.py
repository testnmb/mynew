import requests
import re
import os

# 全局排除关键词定义
EXCLUDE_KEYWORDS = ["成人", "激情", "情色", "涩情", "18禁", "R18"]

class TVSourceProcessor:
    def __init__(self):
        self.all_lines = []
    
    def fetch_url_content(self, url: str):
        try:
            print(f"🔗 获取URL: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'big5']
            content = None
            for encoding in encodings:
                try:
                    content = response.content.decode(encoding)
                    break
                except:
                    continue
            
            if content is None:
                content = response.content.decode('utf-8', errors='ignore')
            
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            print(f"  成功获取 {len(lines)} 行")
            return lines
            
        except Exception as e:
            print(f"  ❌ 获取失败: {e}")
            return []
    
    def fetch_multiple_urls(self, urls: list):
        self.all_lines = []
        for url in urls:
            lines = self.fetch_url_content(url)
            if lines:
                self.all_lines.extend(lines)
        
        if self.all_lines:
            print(f"\n📊 总计获取 {len(self.all_lines)} 行内容")
            # 显示前几行示例
            print("前5行示例:")
            for i, line in enumerate(self.all_lines[:5]):
                print(f"  {i+1}. {line[:80]}..." if len(line) > 80 else f"  {i+1}. {line}")
        else:
            print("\n⚠️  未获取到任何内容")
    
    def remove_excluded_sections(self):
        if not self.all_lines:
            return []
        
        result = []
        in_excluded_section = False
        excluded_count = 0
        
        print(f"\n🔍 开始排除处理...")
        for line in self.all_lines:
            if "#genre#" in line:
                if any(keyword in line for keyword in EXCLUDE_KEYWORDS):
                    if not in_excluded_section:  # 新开始一个排除区域
                        excluded_count += 1
                        print(f"  🚫 排除区域 {excluded_count}: {line[:60]}...")
                    in_excluded_section = True
                else:
                    in_excluded_section = False
                    result.append(line)
            elif not in_excluded_section:
                result.append(line)
        
        print(f"  共排除 {excluded_count} 个区域")
        print(f"  剩余 {len(result)} 行")
        return result
    
    def remove_genre_lines_and_deduplicate(self, lines: list):
        result = []
        seen_urls = set()
        genre_count = 0
        duplicate_count = 0
        
        print(f"\n✨ 开始去重处理...")
        for line in lines:
            # 跳过所有包含#genre#的行
            if "#genre#" in line:
                genre_count += 1
                continue
            
            # 提取URL进行去重
            url_match = re.search(r'(https?://[^\s,]+)', line)
            if url_match:
                url = url_match.group(1)
                if url not in seen_urls:
                    seen_urls.add(url)
                    result.append(line)
                else:
                    duplicate_count += 1
            else:
                # 非URL行直接添加
                result.append(line)
        
        print(f"  删除 {genre_count} 个#genre#行")
        print(f"  移除 {duplicate_count} 个重复URL")
        print(f"  剩余 {len(result)} 行")
        return result
    
    def save_to_file(self, lines: list, filename: str = "my1.txt", first_line: str = "smt,#genre#"):
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            
            # 构建内容
            content = []
            if first_line:
                content.append(first_line)
            content.extend(lines)
            
            # 写入文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            print(f"\n💾 保存文件: {filename}")
            print(f"  行数: {len(content)}")
            print(f"  大小: {os.path.getsize(filename)} 字节")
            
            # 显示保存的内容预览
            print("  前10行预览:")
            for i, line in enumerate(content[:10]):
                print(f"    {i+1}. {line[:80]}..." if len(line) > 80 else f"    {i+1}. {line}")
            
        except Exception as e:
            print(f"\n❌ 保存失败: {e}")
            import traceback
            traceback.print_exc()
    
    def process(self, urls: list, output_file: str = "my1.txt", first_line: str = "smt,#genre#"):
        print("=" * 60)
        print("📺 TV直播源处理工具")
        print("=" * 60)
        print(f"排除关键词: {', '.join(EXCLUDE_KEYWORDS)}")
        print(f"处理URL数: {len(urls)}")
        print(f"输出文件: {output_file}")
        print("=" * 60)
        
        # 1. 获取URL内容
        self.fetch_multiple_urls(urls)
        if not self.all_lines:
            print("\n❌ 错误: 未获取到任何内容，请检查URL是否可访问")
            return
        
        # 2. 排除处理
        filtered_lines = self.remove_excluded_sections()
        if not filtered_lines:
            print("\n⚠️ 警告: 排除后无剩余内容")
            # 即使无内容也保存空文件
            self.save_to_file([], output_file, first_line)
            return
        
        # 3. 去重处理
        final_lines = self.remove_genre_lines_and_deduplicate(filtered_lines)
        
        # 4. 保存结果
        self.save_to_file(final_lines, output_file, first_line)
        
        print("=" * 60)
        print("✅ 处理完成!")
        print("=" * 60)


def main():
    """主处理函数"""
    # 要处理的URL列表
    urls = [
        "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/斯瑪特直播源1",
        #"https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/斯瑪特直播源2",
    ]
   
    # 配置参数
    output_file = "my1.txt"
    first_line = "smt,#genre#"
    
    # 执行处理
    processor = TVSourceProcessor()
    processor.process(urls, output_file, first_line)
    
    # 检查文件是否存在
    if os.path.exists(output_file):
        print(f"\n📁 文件位置: {os.path.abspath(output_file)}")
    else:
        print(f"\n❌ 文件未创建: {output_file}")


if __name__ == "__main__":
    main()
