import requests
import time
from typing import List, Dict, Set
import re

class IPTVProcessor:
    def __init__(self):
        # 定义1：需要写入文件1的类别
        self.categories_file1 = {"新聞", "香港"}
        # 定义2：需要写入文件2的类别
        self.categories_file2 = {"体育", "台湾"}
        
        # 存储从各个URL获取的内容
        self.all_content = []
        
        # 设置请求头，避免被限制
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def fetch_content_from_urls(self, urls: List[str]) -> None:
        """从多个URL获取内容"""
        for i, url in enumerate(urls):
            try:
                print(f"正在从 URL {i+1} 获取内容: {url}")
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                content = response.text
                self.all_content.append(content)
                print(f"✓ 成功从 {url} 获取内容，长度: {len(content)} 字符")
                
                # 添加延迟，避免请求过快
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print(f"✗ 从 {url} 获取内容失败: {e}")
                # 尝试添加重试逻辑
                try:
                    print("尝试重新获取...")
                    response = requests.get(url, headers=self.headers, timeout=20)
                    response.raise_for_status()
                    content = response.text
                    self.all_content.append(content)
                    print(f"✓ 重新获取成功，长度: {len(content)} 字符")
                except:
                    print("重试失败，跳过此URL")
    
    def parse_content(self, content: str) -> Dict[str, List[str]]:
        """解析内容，按类别分组"""
        categories = {}
        current_category = None
        category_lines = []
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是类别行（包含,#genre#）
            if ',#genre#' in line:
                # 保存上一个类别的内容
                if current_category and category_lines:
                    if current_category not in categories:
                        categories[current_category] = []
                    categories[current_category].extend(category_lines)
                
                # 开始新类别
                current_category = line.split(',')[0].strip()
                category_lines = [line]
            elif current_category is not None:
                # 如果是频道行，添加到当前类别
                category_lines.append(line)
        
        # 保存最后一个类别
        if current_category and category_lines:
            if current_category not in categories:
                categories[current_category] = []
            categories[current_category].extend(category_lines)
        
        return categories
    
    def process_contents(self) -> None:
        """处理所有内容并进行分类"""
        all_categories_file1 = {}
        all_categories_file2 = {}
        
        for content_index, content in enumerate(self.all_content):
            print(f"处理内容块 {content_index + 1}...")
            categories = self.parse_content(content)
            
            # 根据定义分类
            for category, lines in categories.items():
                # 去重处理
                unique_lines = []
                seen = set()
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
                
                if category in self.categories_file1:
                    if category not in all_categories_file1:
                        all_categories_file1[category] = []
                    all_categories_file1[category].extend(unique_lines)
                elif category in self.categories_file2:
                    if category not in all_categories_file2:
                        all_categories_file2[category] = []
                    all_categories_file2[category].extend(unique_lines)
        
        # 写入文件
        self.write_to_file("文件1.txt", all_categories_file1)
        self.write_to_file("文件2.txt", all_categories_file2)
        
        # 统计信息
        total_lines_file1 = sum(len(lines) for lines in all_categories_file1.values())
        total_lines_file2 = sum(len(lines) for lines in all_categories_file2.values())
        
        print(f"\n{'='*50}")
        print(f"处理完成！")
        print(f"{'='*50}")
        print(f"文件1.txt 包含 {len(all_categories_file1)} 个类别，共 {total_lines_file1} 行")
        for category in all_categories_file1:
            print(f"  - {category}: {len(all_categories_file1[category])} 行")
        
        print(f"\n文件2.txt 包含 {len(all_categories_file2)} 个类别，共 {total_lines_file2} 行")
        for category in all_categories_file2:
            print(f"  - {category}: {len(all_categories_file2[category])} 行")
        print(f"{'='*50}")
    
    def write_to_file(self, filename: str, categories: Dict[str, List[str]]) -> None:
        """将分类内容写入文件"""
        if not categories:
            print(f"警告: {filename} 没有内容可写入")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# 无相关内容\n")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            for category in sorted(categories.keys()):
                # 获取该类别的所有行并去重
                lines = categories[category]
                unique_lines = []
                seen = set()
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
                
                # 写入文件
                for line in unique_lines:
                    f.write(line + '\n')
                f.write('\n')  # 类别之间空一行
    
    def process_from_urls(self, urls: List[str]) -> None:
        """主处理流程"""
        print("="*50)
        print("IPTV 内容分类处理器")
        print("="*50)
        print(f"目标URL数量: {len(urls)}")
        
        print("\n开始从URL获取内容...")
        self.fetch_content_from_urls(urls)
        
        if not self.all_content:
            print("错误: 未获取到任何内容，程序退出")
            return
        
        total_content_length = sum(len(content) for content in self.all_content)
        print(f"\n获取内容完成，共获取 {len(self.all_content)} 个内容块，总长度: {total_content_length} 字符")
        
        print("\n开始处理内容并分类...")
        self.process_contents()
        
        # 显示文件预览
        self.show_file_preview()

    def show_file_preview(self):
        """显示文件预览"""
        print("\n文件预览:")
        print("-"*30)
        
        try:
            with open("my1.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                print("my1.txt (前20行):")
                for i, line in enumerate(lines[:20]):
                    print(f"{i+1:2}: {line.rstrip()}")
                if len(lines) > 20:
                    print(f"... 省略 {len(lines)-20} 行")
        except FileNotFoundError:
            print("my1.txt 未找到")
        
        print()
        
        try:
            with open("my2.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
                print("my2.txt (前20行):")
                for i, line in enumerate(lines[:20]):
                    print(f"{i+1:2}: {line.rstrip()}")
                if len(lines) > 20:
                    print(f"... 省略 {len(lines)-20} 行")
        except FileNotFoundError:
            print("my2.txt 未找到")


# 主程序
if __name__ == "__main__":
    # 配置URL列表
    urls = [
        "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/%E5%88%AB%E4%BA%BA%E6%94%B6%E8%B4%B9%E6%BA%90",
        "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/%E6%B5%B7%E8%A7%92%E7%A4%BE%E5%8C%BA%E5%8D%9A%E4%B8%BB(%E5%85%8D%E7%95%AA%E5%BC%BA)"
    ]
    
    # 创建处理器实例
    processor = IPTVProcessor()
    
    # 可以根据需要修改类别定义
    # processor.categories_file1 = {"新聞", "香港", "央视", "卫视"}  # 示例
    # processor.categories_file2 = {"体育", "台湾", "电影", "娱乐"}  # 示例
    
    # 执行处理
    try:
        processor.process_from_urls(urls)
        
        print("\n处理完成！文件已保存到:")
        print("  - my1.txt (新聞, 香港 类别)")
        print("  - my2.txt (体育, 台湾 类别)")
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        import traceback
        traceback.print_exc()
