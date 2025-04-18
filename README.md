# PDF转Markdown工具

这是一个将PDF文件转换为Markdown格式的Python工具。该工具特别适合处理大型PDF文件（超过100MB），并提供了进度显示功能。

## 功能特点

- 支持大型PDF文件处理
- 显示转换进度
- 自动清理文本格式
- 保持页面结构
- 支持批量处理
- 自动创建时间戳输出文件

## 目录结构

```
.
├── input/          # 存放待转换的PDF文件
├── output/         # 存放转换后的Markdown文件
├── pdf_to_md.py    # 主程序
└── requirements.txt # 依赖文件
```

## 安装依赖

### 方法1：使用requirements.txt安装

```bash
pip install -r requirements.txt
```

### 方法2：避免重复安装

如果你已经在同一磁盘的其他项目中安装过这些依赖，可以：

1. **检查已安装的包**：
   ```bash
   pip list | findstr "pdfplumber tqdm"
   ```
   如果已经安装了这些包，可以跳过安装步骤。

2. **使用虚拟环境**：
   如果你在其他项目中已经创建了包含这些包的虚拟环境，可以直接使用那个环境：
   ```bash
   # 激活已有的虚拟环境
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **使用--no-deps选项**：
   如果只想安装缺失的包：
   ```bash
   pip install --no-deps -r requirements.txt
   ```

## 使用方法

1. 将需要转换的PDF文件放入 `input` 文件夹

2. 运行程序的方式：

   a. 批量处理input文件夹中的所有PDF文件：
   ```bash
   python pdf_to_md.py --batch
   ```

   b. 转换单个指定的PDF文件：
   ```bash
   python pdf_to_md.py --file 你的文件.pdf
   ```

   c. 转换单个文件并指定输出路径：
   ```bash
   python pdf_to_md.py --file 你的文件.pdf -o 输出文件.md
   ```

## 输出文件

- 转换后的文件会自动保存在 `output` 文件夹中
- 输出文件名格式：`原文件名_时间戳.md`
- 时间戳格式：YYYYMMDD_HHMMSS

## 注意事项

1. 确保有足够的磁盘空间
2. 转换大文件时可能需要较长时间
3. 建议在转换前备份原始PDF文件
4. 程序会自动创建 `input` 和 `output` 文件夹（如果不存在）

## 错误处理

程序会处理常见的错误情况：
- 文件不存在
- 文件格式错误
- 内存不足
- 权限问题

如果遇到任何错误，程序会显示详细的错误信息。 