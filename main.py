#!/usr/bin/env python3
# process_iptv.py - 处理IPTV源文件并分类去重
import requests
import time
import os
import hashlib
from typing import List, Dict, Set, Tuple
from datetime import datetime
from collections import defaultdict


class IPTVProcessor:
    def __init__(self):
        # 定义1：需要写入文件1的类别
        self.categories_file1 = {
            "电影", "新闻", "体育", "台湾", "中国", 
            "香港", "韩国", "印度", "日本", "越南", 
            "泰国", "新加坡", "英国", "马来西亚", 
            "儿童", "纪录"
        }
        
        # 定义2：需要写入文件2的类别
        self.categories_file2 = {
            "【1】", "【2】", "【3】", "【4】", "【5】", 
            "【6】", "【7】", "【8】", "【9】", "【10】", 
            "【11】", "【12】", "【13】", "【14】", "【15】", "【16】"
        }
        
        # 源URL列表
        self.source_urls = [
            "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/斯瑪特直播源1",
            "https://raw.githubusercontent.com/FGBLH/FG/refs/heads/main/%E6%B5%B7%E8%A7%92%E7%A4%BE%E5%8C%BA%E5%8D%9A%E4%B8%BB(%E5%85%8D%E7%95%AA%E5%BC%BA)"
        ]
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/plain',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # 存储原始分组
        self.raw_groups = []  # 存储 (category, lines)
        
        # 去重相关
        self.url_signatures = set()  # 存储URL的签名用于源去重
        
        # 统计信息
        self.stats = {
            'total_urls': 0,
            'success_urls': 0,
            'duplicate_channels': 0,
            'unique_channels': 0,
            'file1_categories': set(),
            'file2_categories': set()
        }
    
    def fetch_content(self, url: str) -> Tuple[str, bool]:
        """从URL获取内容，返回内容和是否成功"""
        try:
            print(f"📡 正在获取: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # 计算内容签名用于去重
            content_hash = hashlib.md5(response.content).hexdigest()
            if content_hash in self.url_signatures:
                print(f"⚠️  检测到重复源内容，跳过: {url}")
                return "", False
                
            self.url_signatures.add(content_hash)
            self.stats['success_urls'] += 1
            return response.text, True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取失败 {url}: {e}")
            return "", False
        except Exception as e:
            print(f"❌ 处理URL时出错 {url}: {e}")
            return "", False
    
    def extract_channel_info(self, line: str) -> Tuple[str, str, str]:
        """从频道行提取信息，返回(频道名, URL, 签名)"""
        parts = line.split(',')
        if len(parts) >= 2:
            channel_name = parts[0].strip()
            channel_url = parts[1].strip()
            # 创建频道签名（使用名称和URL的组合）
            # 对URL进行标准化处理，去除可能的查询参数差异
            clean_url = channel_url.split('?')[0] if '?' in channel_url else channel_url
            signature = hashlib.md5(f"{channel_name}:{clean_url}".encode()).hexdigest()
            return channel_name, channel_url, signature
        return "", "", ""
    
    def process_content(self, content: str):
        """处理内容并存储原始分组"""
        if not content:
            return
            
        current_group = []
        current_category = ""
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是分组标题行
            if line.endswith(",#genre#"):
                # 保存上一个分组
                if current_group and current_category:
                    self.raw_groups.append((current_category, current_group))
                
                # 开始新分组
                current_category = line.split(',')[0]
                current_group = [line]
            else:
                # 添加频道行到当前分组
                if current_group is not None:
                    current_group.append(line)
        
        # 处理最后一个分组
        if current_group and current_category:
            self.raw_groups.append((current_category, current_group))
    
    def classify_and_deduplicate(self) -> Tuple[List[Dict], List[Dict]]:
        """分类并整体去重，返回(file1_content, file2_content)"""
        # 按文件分类收集频道
        file1_channels = defaultdict(list)  # category -> [(channel_name, channel_line, signature)]
        file2_channels = defaultdict(list)
        
        file1_signatures = set()  # 用于file1整体去重
        file2_signatures = set()  # 用于file2整体去重
        
        print("🔍 分类和去重处理...")
        
        for category, lines in self.raw_groups:
            if len(lines) <= 1:  # 只有标题没有频道
                continue
            
            # 确定属于哪个文件
            target_file = None
            for cat1 in self.categories_file1:
                if cat1 in category:
                    target_file = 1
                    self.stats['file1_categories'].add(category)
                    break
            
            if not target_file:
                for cat2 in self.categories_file2:
                    if cat2 in category:
                        target_file = 2
                        self.stats['file2_categories'].add(category)
                        break
            
            if not target_file:
                continue  # 不匹配任何类别，跳过
            
            # 处理每个频道
            title_line = lines[0]
            for channel_line in lines[1:]:
                channel_name, channel_url, signature = self.extract_channel_info(channel_line)
                if not signature:
                    continue
                
                # 根据目标文件进行去重
                if target_file == 1:
                    if signature not in file1_signatures:
                        file1_signatures.add(signature)
                        file1_channels[category].append((channel_name, channel_line, signature))
                        self.stats['unique_channels'] += 1
                    else:
                        self.stats['duplicate_channels'] += 1
                else:  # target_file == 2
                    if signature not in file2_signatures:
                        file2_signatures.add(signature)
                        file2_channels[category].append((channel_name, channel_line, signature))
                        self.stats['unique_channels'] += 1
                    else:
                        self.stats['duplicate_channels'] += 1
        
        # 构建最终输出结构
        file1_content = []
        file2_content = []
        
        # 构建file1内容
        for category, channels in file1_channels.items():
            if channels:  # 有实际频道才添加
                lines = [f"{category},#genre#"]
                for _, channel_line, _ in channels:
                    lines.append(channel_line)
                file1_content.append({"category": category, "lines": lines})
        
        # 构建file2内容
        for category, channels in file2_channels.items():
            if channels:  # 有实际频道才添加
                lines = [f"{category},#genre#"]
                for _, channel_line, _ in channels:
                    lines.append(channel_line)
                file2_content.append({"category": category, "lines": lines})
        
        # 按分类名称排序，使输出更有序
        file1_content.sort(key=lambda x: x["category"])
        file2_content.sort(key=lambda x: x["category"])
        
        return file1_content, file2_content
    
    def write_files(self, file1_content: List[Dict], file2_content: List[Dict]):
        """写入文件"""
        # 写入my1.txt
        self._write_single_file("my1.txt", file1_content, "文件1", self.stats['file1_categories'])
        
        # 写入my2.txt
        self._write_single_file("my2.txt", file2_content, "文件2", self.stats['file2_categories'])
    
    def _write_single_file(self, filename: str, content_list: List[Dict], file_desc: str, categories: Set):
        """写入单个文件"""
        total_channels = sum(len(item["lines"]) - 1 for item in content_list)
        
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入文件头
            f.write(f"# IPTV源文件 - {file_desc}\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 源URL: {', '.join(self.source_urls)}\n")
            f.write(f"# 分组数量: {len(content_list)}\n")
            f.write(f"# 频道数量: {total_channels}\n")
            f.write(f"# 去重策略: 文件整体去重（相同频道只出现一次）\n")
            f.write("# " + "="*60 + "\n\n")
            
            # 写入内容
            for item in content_list:
                for line in item["lines"]:
                    f.write(line + "\n")
                f.write("\n")  # 分组之间空一行
        
        # 输出结果
        if total_channels > 0:
            categories_list = sorted(list(categories))
            print(f"✅ {filename}: {len(content_list)}个分组, {total_channels}个唯一频道")
            if categories_list:
                print(f"   包含分类: {', '.join(categories_list[:5])}")
                if len(categories_list) > 5:
                    print(f"             等共{len(categories_list)}个分类")
        else:
            print(f"⚠️  {filename}: 没有内容可写入")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {file_desc} - 暂无内容\n")
    
    def run(self):
        """主运行方法"""
        print("="*60)
        print("🎬 IPTV源文件处理工具 (整体去重)")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 获取并处理所有源
        self.stats['total_urls'] = len(self.source_urls)
        
        for idx, url in enumerate(self.source_urls, 1):
            print(f"\n📋 处理源 {idx}/{len(self.source_urls)}")
            content, success = self.fetch_content(url)
            if success and content:
                self.process_content(content)
                time.sleep(0.3)  # 礼貌延迟
        
        # 分类并整体去重
        print("\n🔧 进行整体去重处理...")
        file1_content, file2_content = self.classify_and_deduplicate()
        
        # 写入文件
        print("\n💾 写入文件...")
        self.write_files(file1_content, file2_content)
        
        # 输出统计信息
        self.print_statistics(file1_content, file2_content)
        
        print("="*60)
        print("🎉 处理完成!")
        print("="*60)
    
    def print_statistics(self, file1_content: List[Dict], file2_content: List[Dict]):
        """打印详细统计信息"""
        print("\n📊 详细统计信息:")
        print("-" * 60)
        
        # 总体统计
        print(f"🌐 源处理统计:")
        print(f"   总URL数量: {self.stats['total_urls']}")
        print(f"   成功获取: {self.stats['success_urls']}")
        print(f"   重复内容源: {self.stats['total_urls'] - self.stats['success_urls']}")
        
        # 频道统计
        print(f"\n📺 频道统计:")
        print(f"   唯一频道数: {self.stats['unique_channels']:,}")
        print(f"   过滤重复频道数: {self.stats['duplicate_channels']:,}")
        print(f"   总发现频道数: {self.stats['unique_channels'] + self.stats['duplicate_channels']:,}")
        
        # 文件1统计
        if file1_content:
            channels1 = sum(len(item["lines"]) - 1 for item in file1_content)
            categories1 = list(self.stats['file1_categories'])
            print(f"\n📁 my1.txt (匹配类别: {len(self.categories_file1)}个)")
            print(f"   分组数量: {len(file1_content)}")
            print(f"   频道数量: {channels1}")
            print(f"   分类数量: {len(categories1)}")
            if categories1:
                print(f"   分类列表: {', '.join(sorted(categories1)[:6])}")
                if len(categories1) > 6:
                    print(f"             等{len(categories1)}个分类")
        else:
            print(f"\n📁 my1.txt: 无匹配内容")
        
        # 文件2统计
        if file2_content:
            channels2 = sum(len(item["lines"]) - 1 for item in file2_content)
            categories2 = list(self.stats['file2_categories'])
            print(f"\n📁 my2.txt (匹配类别: {len(self.categories_file2)}个)")
            print(f"   分组数量: {len(file2_content)}")
            print(f"   频道数量: {channels2}")
            print(f"   分类数量: {len(categories2)}")
            if categories2:
                print(f"   分类列表: {', '.join(sorted(categories2)[:6])}")
                if len(categories2) > 6:
                    print(f"             等{len(categories2)}个分类")
        else:
            print(f"\n📁 my2.txt: 无匹配内容")


def main():
    """主函数"""
    processor = IPTVProcessor()
    
    try:
        processor.run()
        
        # 验证文件
        print("\n🔍 文件验证:")
        for filename in ["my1.txt", "my2.txt"]:
            try:
                if os.path.exists(filename):
                    size = os.path.getsize(filename)
                    lines_count = 0
                    with open(filename, 'r', encoding='utf-8') as f:
                        lines_count = len(f.readlines())
                    
                    # 统计频道数
                    channel_count = 0
                    with open(filename, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#') and ',#genre#' not in line:
                                channel_count += 1
                    
                    print(f"   📄 {filename}:")
                    print(f"      大小: {size:,} 字节")
                    print(f"      行数: {lines_count}")
                    print(f"      频道数: {channel_count}")
                    
                    if size < 100:
                        print(f"      ⚠️  文件过小，可能为空")
                else:
                    print(f"   ⚠️  {filename}: 文件未生成")
            except Exception as e:
                print(f"   ❌ {filename}: 验证出错 - {e}")
                
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
