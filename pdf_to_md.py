import pdfplumber
import os
from tqdm import tqdm
import argparse
import re
import shutil
from datetime import datetime

# 定义输入输出文件夹
INPUT_DIR = "input"
OUTPUT_DIR = "output"

def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def clean_text(text):
    """清理文本，保留更多原始格式"""
    if not text:
        return ""
    
    # 移除多余的空白字符，但保留段落结构
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # 修复常见的OCR错误
    text = text.replace('，', '，').replace('。', '。')
    text = text.replace('：', '：').replace('；', '；')
    
    # 修复常见的断行问题
    text = re.sub(r'([。！？；])[ \t]*\n', r'\1\n\n', text)
    
    # 修复标题格式
    text = re.sub(r'^第([一二三四五六七八九十]+)章\s*', r'## 第\1章 ', text, flags=re.MULTILINE)
    text = re.sub(r'^([一二三四五六七八九十]+)[.、]\s*', r'### \1. ', text, flags=re.MULTILINE)
    
    return text.strip()

def is_title(text):
    """判断文本是否为标题"""
    # 标题通常较短，且以特定字符结尾
    if len(text) < 50 and re.search(r'[。：]$', text):
        return True
    
    # 检查是否匹配标题模式
    title_patterns = [
        r'^第[一二三四五六七八九十]+章',
        r'^[一二三四五六七八九十]+[.、]',
        r'^[0-9]+[.、]',
        r'^[A-Z][.、]'
    ]
    
    for pattern in title_patterns:
        if re.match(pattern, text.strip()):
            return True
    
    return False

def format_paragraph(text):
    """格式化段落"""
    # 分割成行
    lines = text.split('\n')
    formatted_lines = []
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph:
                formatted_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            formatted_lines.append('')
        else:
            # 如果是标题，单独处理
            if is_title(line):
                if current_paragraph:
                    formatted_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                formatted_lines.append(line)
            else:
                current_paragraph.append(line)
    
    # 处理最后一个段落
    if current_paragraph:
        formatted_lines.append(' '.join(current_paragraph))
    
    return '\n'.join(formatted_lines)

def extract_tables(page):
    """提取表格并转换为Markdown格式"""
    tables = page.extract_tables()
    if not tables:
        return ""
    
    markdown_tables = []
    for table in tables:
        if not table or not table[0]:
            continue
            
        # 创建表头
        header = '| ' + ' | '.join(str(cell) if cell else '' for cell in table[0]) + ' |'
        separator = '| ' + ' | '.join(['---'] * len(table[0])) + ' |'
        
        # 创建表格内容
        rows = []
        for row in table[1:]:
            if not row:
                continue
            rows.append('| ' + ' | '.join(str(cell) if cell else '' for cell in row) + ' |')
        
        # 组合表格
        markdown_table = '\n'.join([header, separator] + rows)
        markdown_tables.append(markdown_table)
    
    return '\n\n'.join(markdown_tables)

def get_output_path(pdf_path):
    """生成输出文件路径"""
    # 获取文件名（不含扩展名）
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    # 添加时间戳以避免文件名冲突
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{base_name}_{timestamp}.md")

def convert_pdf_to_md(pdf_path, output_path=None):
    """
    将PDF文件转换为Markdown格式
    
    Args:
        pdf_path (str): PDF文件路径
        output_path (str, optional): 输出文件路径，如果不指定则使用默认路径
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    if output_path is None:
        output_path = get_output_path(pdf_path)
    
    try:
        # 打开PDF文件
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"开始转换PDF文件: {pdf_path}")
            print(f"总页数: {total_pages}")
            
            # 创建进度条
            with open(output_path, 'w', encoding='utf-8') as md_file:
                # 写入标题
                title = os.path.splitext(os.path.basename(pdf_path))[0]
                md_file.write(f"# {title}\n\n")
                
                # 处理每一页
                for page_num in tqdm(range(total_pages), desc="转换进度"):
                    page = pdf.pages[page_num]
                    
                    # 提取文本
                    text = page.extract_text()
                    
                    # 提取表格
                    tables = extract_tables(page)
                    
                    if text or tables:
                        # 写入页码
                        md_file.write(f"## 第 {page_num + 1} 页\n\n")
                        
                        # 处理文本
                        if text:
                            # 清理和格式化文本
                            cleaned_text = clean_text(text)
                            formatted_text = format_paragraph(cleaned_text)
                            md_file.write(formatted_text + "\n\n")
                        
                        # 处理表格
                        if tables:
                            md_file.write(tables + "\n\n")
                        
                        # 添加页面分隔符
                        md_file.write("---\n\n")
            
            print(f"\n转换完成！输出文件保存在: {output_path}")
            
    except Exception as e:
        print(f"转换过程中出现错误: {str(e)}")
        raise

def process_input_directory():
    """处理input目录中的所有PDF文件"""
    ensure_directories()
    
    # 获取input目录中的所有PDF文件
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"在 {INPUT_DIR} 目录中没有找到PDF文件")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    # 处理每个PDF文件
    for pdf_file in pdf_files:
        pdf_path = os.path.join(INPUT_DIR, pdf_file)
        try:
            convert_pdf_to_md(pdf_path)
        except Exception as e:
            print(f"处理文件 {pdf_file} 时出错: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='将PDF文件转换为Markdown格式')
    parser.add_argument('--file', help='单个PDF文件路径（可选）')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    parser.add_argument('--batch', action='store_true', help='处理input目录中的所有PDF文件')
    
    args = parser.parse_args()
    
    try:
        if args.batch:
            process_input_directory()
        elif args.file:
            convert_pdf_to_md(args.file, args.output)
        else:
            print("请指定要转换的PDF文件或使用 --batch 处理input目录中的所有文件")
            return 1
            
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 