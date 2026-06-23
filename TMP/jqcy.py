import requests

def fetch_and_save():
    url = "http://nas.jqcykj.com:88"
    output_file = "jqcy.txt"
    
    try:
        # 获取原始字节数据
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # ---------- 智能编码检测 ----------
        # 1. 优先使用 requests 基于 chardet 的 apparent_encoding
        if response.apparent_encoding:
            response.encoding = response.apparent_encoding
        else:
            # 2. 若检测失败，尝试中文常用的 GBK 编码（也可尝试 gb18030）
            response.encoding = 'gbk'
        # 如果仍不行，可手动改为 'gb18030' 或 'utf-8'
        # ---------------------------------
        
        content = response.text  # 此时应正确解码
        
        # 按行分割
        lines = content.splitlines()
        
        # 过滤包含 '#genre#' 的行（不区分大小写）
        filtered_lines = [line for line in lines if '#genre#' not in line.lower()]
        
        # 写入文件（UTF-8 编码以兼容大多数编辑器）
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("jqcy,#genre#\n")
            for line in filtered_lines:
                f.write(line + '\n')
        
        print(f"✅ 成功保存到 {output_file}，共写入 {len(filtered_lines) + 1} 行。")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    fetch_and_save()
