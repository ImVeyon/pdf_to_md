import pdfplumber
import os
from tqdm import tqdm
import argparse
import re
import shutil
from datetime import datetime
from collections import defaultdict

# 定义输入输出文件夹
INPUT_DIR = "input"
OUTPUT_DIR = "output"

# 定义标题关键词
CHAPTER_KEYWORDS = [
    r'^第[一二三四五六七八九十]+章',
    r'^[一二三四五六七八九十]+、',
    r'^[0-9]+[.、]',
    r'^[A-Z][.、]',
    r'^[a-z][.、]',
    r'^[①②③④⑤⑥⑦⑧⑨⑩]',
    r'^[（(][一二三四五六七八九十][)）]',
    r'^[（(][0-9]+[)）]'
]

def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_font_info(text_obj):
    """获取文本的字体信息"""
    if not text_obj:
        return None
    font_name = text_obj.get('fontname', '').lower()
    font_size = text_obj.get('size', 0)
    return {
        'name': font_name,
        'size': font_size,
        'is_bold': 'bold' in font_name or 'black' in font_name,
        'is_italic': 'italic' in font_name or 'oblique' in font_name
    }

def analyze_page_font_sizes(page):
    """分析页面中的字体大小分布"""
    font_sizes = []
    for obj in page.extract_words(keep_blank_chars=True, x_tolerance=3, y_tolerance=3):
        font_info = get_font_info(obj)
        if font_info and font_info['size'] > 0:
            font_sizes.append(font_info['size'])
    
    if not font_sizes:
        return None
    
    # 计算字体大小的分布
    font_sizes.sort()
    total = len(font_sizes)
    
    # 使用百分位数来划分字体大小等级
    percentiles = {
        'h4': font_sizes[int(total * 0.95)],  # 最大的5%作为h4
        'h5': font_sizes[int(total * 0.85)],  # 接下来的10%作为h5
        'h6': font_sizes[int(total * 0.75)]   # 接下来的10%作为h6
    }
    
    return percentiles

def is_semantic_title(text):
    """基于语义判断是否为标题"""
    if not text:
        return False, 0
    
    text = text.strip()
    
    # 检查是否匹配标题关键词
    for pattern in CHAPTER_KEYWORDS:
        if re.match(pattern, text):
            # 根据不同的模式确定标题级别
            if re.match(r'^第[一二三四五六七八九十]+章', text):
                return True, 1
            elif re.match(r'^[一二三四五六七八九十]+、', text):
                return True, 2
            elif re.match(r'^[0-9]+[.、]', text):
                return True, 2
            elif re.match(r'^[A-Z][.、]', text):
                return True, 3
            elif re.match(r'^[a-z][.、]', text):
                return True, 3
            elif re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', text):
                return True, 3
            elif re.match(r'^[（(][一二三四五六七八九十][)）]', text):
                return True, 4
            elif re.match(r'^[（(][0-9]+[)）]', text):
                return True, 4
    
    # 检查其他标题特征
    if len(text) < 50 and text.endswith('：'):
        return True, 3
    
    return False, 0

def get_title_level(text, font_info, font_percentiles):
    """综合判断标题级别"""
    if not text:
        return 0
    
    # 首先检查语义标题
    is_title_text, semantic_level = is_semantic_title(text)
    if is_title_text:
        return semantic_level
    
    # 如果不是语义标题，则根据字体大小判断
    if font_info and font_info['size'] and font_percentiles:
        if font_info['size'] >= font_percentiles['h4']:
            return 4
        elif font_info['size'] >= font_percentiles['h5']:
            return 5
        elif font_info['size'] >= font_percentiles['h6']:
            return 6
    
    return 0

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
    
    return text.strip()

def format_text_with_style(text, font_info):
    """根据字体信息格式化文本"""
    if not text:
        return text
    
    # 处理加粗
    if font_info and font_info['is_bold']:
        text = f"**{text}**"
    
    # 处理斜体
    if font_info and font_info['is_italic']:
        text = f"*{text}*"
    
    return text

def process_text_objects(page):
    """处理页面中的文本对象，保持原始格式"""
    text_objects = []
    current_paragraph = []
    current_font = None
    
    # 分析页面字体大小分布
    font_percentiles = analyze_page_font_sizes(page)
    
    for obj in page.extract_words(keep_blank_chars=True, x_tolerance=3, y_tolerance=3):
        text = obj['text']
        font_info = get_font_info(obj)
        
        # 获取标题级别
        title_level = get_title_level(text, font_info, font_percentiles)
        
        if title_level > 0:
            # 处理之前的段落
            if current_paragraph:
                text_objects.append({
                    'type': 'paragraph',
                    'text': ' '.join(current_paragraph),
                    'font_info': current_font
                })
                current_paragraph = []
            
            # 添加标题
            text_objects.append({
                'type': f'h{title_level}',
                'text': text,
                'font_info': font_info
            })
        else:
            # 处理普通文本
            if not current_paragraph:
                current_font = font_info
            current_paragraph.append(text)
    
    # 处理最后一个段落
    if current_paragraph:
        text_objects.append({
            'type': 'paragraph',
            'text': ' '.join(current_paragraph),
            'font_info': current_font
        })
    
    return text_objects

def convert_to_markdown(text_objects):
    """将处理后的文本对象转换为Markdown格式"""
    markdown_lines = []
    
    for obj in text_objects:
        text = obj['text']
        obj_type = obj['type']
        font_info = obj['font_info']
        
        if obj_type.startswith('h'):
            # 处理标题
            level = int(obj_type[1])
            markdown_lines.append(f"{'#' * level} {text}\n")
        elif obj_type == 'paragraph':
            # 处理段落
            formatted_text = format_text_with_style(text, font_info)
            markdown_lines.append(f"{formatted_text}\n\n")
    
    return ''.join(markdown_lines)

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
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{base_name}_{timestamp}.md")

def convert_pdf_to_md(pdf_path, output_path=None):
    """将PDF文件转换为Markdown格式"""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    if output_path is None:
        output_path = get_output_path(pdf_path)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"开始转换PDF文件: {pdf_path}")
            print(f"总页数: {total_pages}")
            
            with open(output_path, 'w', encoding='utf-8') as md_file:
                # 写入标题
                title = os.path.splitext(os.path.basename(pdf_path))[0]
                md_file.write(f"# {title}\n\n")
                
                # 处理每一页
                for page_num in tqdm(range(total_pages), desc="转换进度"):
                    page = pdf.pages[page_num]
                    
                    # 处理文本对象
                    text_objects = process_text_objects(page)
                    markdown_text = convert_to_markdown(text_objects)
                    
                    # 提取表格
                    tables = extract_tables(page)
                    
                    if markdown_text or tables:
                        # 写入页码
                        md_file.write(f"## 第 {page_num + 1} 页\n\n")
                        
                        # 写入处理后的文本
                        if markdown_text:
                            md_file.write(markdown_text)
                        
                        # 写入表格
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
    
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"在 {INPUT_DIR} 目录中没有找到PDF文件")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
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