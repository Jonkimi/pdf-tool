# PDF and Word Document Processing Tools

This repository contains a collection of Python scripts for processing and compressing PDF and Word documents.

## Features

*   **Convert Word to PDF**: Converts `.docx` files to `.pdf`.
*   **Image ompression**: Compresses images within Word documents before converting to PDF.
*   **PDF Compression**: Compresses existing PDF files using Ghostscript to reduce file size.
*   **PDF Labeling**: Adds the filename as a label to the first page of a PDF.

---

# PDF 及 Word 文档处理工具

本代码仓库包含一系列用于处理和压缩 PDF 及 Word 文档的 Python 脚本。

## 功能

*   **Word 转 PDF**: 将 `.docx` 文件转换为 `.pdf` 文件。
*   **图片压缩**: 在将 Word 文档转换为 PDF 之前，预先压缩其中的图片以减小文件体积。
*   **PDF 压缩**: 使用 Ghostscript 压缩已有的 PDF 文件以减小文件大小。
*   **PDF 标注**: 将文件名作为标签添加到 PDF 的第一页。

## Requirements

*   Python 3.x
*   Ghostscript: Must be installed and accessible from the command line.
*   Required Python packages can be installed using [uv](https://astral.sh/uv) (recommended) or pip:
    ```bash
    uv pip install docx2pdf pypdf reportlab pillow python-docx PyMuPDF
    # or
    pip install docx2pdf pypdf reportlab pillow python-docx PyMuPDF
    ```

## 备忘

*   Python 3.x
*   Ghostscript: 必须已安装并在命令行中可用。
*   所需的 Python 包可以使用 [uv](https://astral.sh/uv) (推荐) 或 pip 安装：
    ```bash
    uv pip install docx2pdf pypdf reportlab pillow python-docx PyMuPDF
    # 或
    pip install docx2pdf pypdf reportlab pillow python-docx PyMuPDF
    ```

## Usage

Each script is designed to be run from the command line and can be configured by editing the variables at the top of each file.

### `process_doc.py`

This script converts Word documents (`.docx`) to PDF. It first compresses images within the `.docx` file before converting it to reduce the final file size.

1.  Place your `.docx` files in the `主体结构` directory (or change the `INPUT_DIR` variable in the script).
2.  Run the script:
    ```bash
    python process_doc.py
    ```
3.  The converted PDF files will be saved in the `output_pdfs` directory (or the configured `OUTPUT_DIR`).

### `process_pdf.py`

This script compresses PDF files using Ghostscript.

1.  Place the PDF files you want to compress into the `output_pdfs` directory (or change the `INPUT_DIR` variable). This is conveniently the output directory of `process_doc.py`.
2.  Run the script:
    ```bash
    python process_pdf.py
    ```
3.  The compressed PDFs will be saved in the `compressed_pdfs` directory (or the configured `OUTPUT_DIR`).

| 参数 | 屏幕阅读 | 打印用途 |
| --- | --- | --- |
| `target_dpi` | 150 | 300 |
| `threshold` | 1.0 | 1.5 |
| `image_quality` | 75 | 85 |

### `label_pdf.py`

This script adds a label with the filename to the top-left corner of the first page of a PDF.

1.  Place the PDF files you want to label in the `主体结构压缩` directory (or change `INPUT_DIR`).
2.  Run the script:
    ```bash
    python label_pdf.py
    ```
3.  The labeled PDFs will be saved in the `labeled_pdfs` directory (or the configured `OUTPUT_DIR`).

## 使用说明

每个脚本都可以从命令行运行，并通过编辑文件顶部的变量进行配置。

### `process_doc.py`

该脚本将 Word 文档（`.docx`）转换为 PDF。它会先压缩 `.docx` 文件中的图片，然后再进行转换，以减小最终文件大小。

1.  将您的 `.docx` 文件放入 `主体结构` 目录（或在脚本中更改 `INPUT_DIR` 变量）。
2.  运行脚本：
    ```bash
    python process_doc.py
    ```
3.  转换后的 PDF 文件将保存在 `output_pdfs` 目录（或配置的 `OUTPUT_DIR`）中。

### `process_pdf.py`

该脚本使用 Ghostscript 压缩 PDF 文件。

1.  将需要压缩的 PDF 文件放入 `output_pdfs` 目录（或更改 `INPUT_DIR` 变量）。该目录恰好是 `process_doc.py` 的输出目录。
2.  运行脚本：
    ```bash
    python process_pdf.py
    ```
3.  压缩后的 PDF 将保存在 `compressed_pdfs` 目录（或配置的 `OUTPUT_DIR`）中。

### `label_pdf.py`

该脚本在 PDF 的第一页左上角添加一个带有文件名的标签。

1.  将需要标注的 PDF 文件放入 `主体结构压缩` 目录（或更改 `INPUT_DIR`）。
2.  运行脚本：
    ```bash
    python label_pdf.py
    ```
3.  标注后的 PDF 将保存在 `labeled_pdfs` 目录（或配置的 `OUTPUT_DIR`）中。

## Development

### Running from source

It is recommended to use [uv](https://astral.sh/uv) for dependency management:

```bash
# Install dependencies and create virtual environment
uv sync

# Run the application
uv run main.py
```

Or using standard pip:

```bash
pip install -r requirements.txt
python main.py
```

### Building and Packaging

The application can be packaged into a standalone executable for different platforms using PyInstaller.

#### Prerequisites

Install the development dependencies:

```bash
uv pip install pyinstaller
# or
pip install pyinstaller
```

#### Local Build

To build for your current platform, run:

```bash
cd packaging
uv run build.py
# or
python build.py
```

The resulting executable or app bundle will be located in `packaging/dist/`.

#### Multi-platform Packaging

Multi-platform builds are handled automatically via GitHub Actions whenever a new tag starting with `v` is pushed.

## License

This project is licensed under the terms of the LICENSE file.
