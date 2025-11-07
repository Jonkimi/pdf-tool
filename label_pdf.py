import io
from pathlib import Path  # 导入 Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import red
from reportlab.lib.units import inch

# --- 导入字体相关的模块 ---
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# --- 配置 ---
INPUT_DIR = Path("./主体结构压缩")  # 包含 PDF 文件的输入目录 (使用 / 操作符连接路径)
OUTPUT_DIR = Path("./labeled_pdfs")  # 保存处理后 PDF 的输出目录

# --- 字体配置 (！！！重要：请根据你的系统修改 ！！！) ---
# 1. 选择一个你系统上存在且支持中文的字体文件路径
#    ttf 或 ttc 文件都可以。ttc 是字体集合，可能需要指定索引 (subfontIndex)。

# --- Windows 示例 ---
# font_path = Path("C:/Windows/Fonts/simsun.ttc")  # 宋体 (可能需要 subfontIndex=0)
# font_path = Path("C:/Windows/Fonts/msyh.ttc")    # 微软雅黑 (可能需要 subfontIndex=0)
font_path = Path("C:/Windows/Fonts/simhei.ttf")  # 黑体 (通常不需要索引)

# --- macOS 示例 ---
# font_path = Path("/System/Library/Fonts/PingFang.ttc") # 苹方 SC (可能需要 subfontIndex=0 或其他)
# font_path = Path("/Library/Fonts/Arial Unicode MS.ttf") # 如果安装了

# --- Linux 示例 (路径可能不同) ---
# font_path = Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc") # 文泉驿正黑
# font_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf") # Noto Sans CJK

# *** 确认上面的 `font_path` 指向你系统中一个有效的、支持中文的字体文件 ***

# 2. 给这个字体在 ReportLab 中起一个名字
registered_font_name = "MyChineseFont"

# 3. 注册字体
font_registered = False
if font_path.exists():
    try:
        # 处理 .ttc (TrueType Collection)，需要指定字体索引，0 通常是第一个
        if font_path.suffix.lower() == ".ttc":
            pdfmetrics.registerFont(
                TTFont(registered_font_name, font_path, subfontIndex=0)
            )
        else:  # 处理 .ttf, .otf
            pdfmetrics.registerFont(TTFont(registered_font_name, font_path))
        font_registered = True
        print(f"成功注册字体: '{font_path}' as '{registered_font_name}'")
    except Exception as e:
        print(f"错误：注册字体 '{font_path}' 失败: {e}")
        print("请检查字体文件是否有效，或者尝试 TTC 的其他索引 (subfontIndex)。")
else:
    print(f"错误：字体文件未找到: '{font_path}'")
    print("请修改脚本中的 'font_path' 指向一个有效的字体文件路径。")

if not font_registered:
    print(
        "警告：未使用自定义中文字体，文件名中的中文可能显示为乱码或方块。将回退到 Helvetica。"
    )
    registered_font_name = "Helvetica"  # 回退到默认字体（无法显示中文）
# --- /字体配置 ---


def add_filename_to_pdf(input_pdf_path: Path, output_pdf_path: Path):
    """
    向 PDF 文件的第一页添加其文件名作为文本。

    Args:
        input_pdf_path (Path): 输入 PDF 文件的 Path 对象。
        output_pdf_path (Path): 输出 PDF 文件的 Path 对象。
    """
    # 1. 获取纯文件名（不含路径）用于显示
    display_filename = input_pdf_path.name  # 使用 .name 属性

    try:
        # 2. 读取原始 PDF 获取第一页尺寸
        reader = PdfReader(input_pdf_path)  # pypdf 可以直接接受 Path 对象
        if not reader.pages:
            print(f"警告：文件 '{display_filename}' 没有页面，已跳过。")
            return False  # 表示处理失败或跳过

        first_page = reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)

        # 3. 创建包含文件名的水印 PDF (在内存中)
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # --- 自定义文本外观和位置 ---
        font_size = 10
        text_color = red
        margin = 0.5 * inch
        x_position = margin
        y_position = page_height - margin * 0.5 - font_size  # 左上角

        can.setFont(registered_font_name, font_size)
        can.setFillColor(text_color)
        can.drawString(x_position, y_position, display_filename)  # 使用纯文件名

        can.save()

        # 4. 将水印 PDF 合并到原始 PDF 的第一页
        packet.seek(0)
        watermark_reader = PdfReader(packet)
        watermark_page = watermark_reader.pages[0]

        writer = PdfWriter()
        first_page.merge_page(watermark_page)
        writer.add_page(first_page)  # 添加修改后的第一页

        # 添加原始 PDF 的剩余页面
        for i in range(1, len(reader.pages)):
            writer.add_page(reader.pages[i])

        # 5. 保存结果到输出文件
        # 确保输出目录存在 (主函数会创建，这里多一层保险)
        output_pdf_path.parent.mkdir(
            parents=True, exist_ok=True
        )  # 使用 .parent 和 .mkdir()
        with open(
            output_pdf_path, "wb"
        ) as output_file:  # open() 可以直接接受 Path 对象
            writer.write(output_file)

        return True  # 表示处理成功

    except Exception as e:
        print(f"处理文件 '{display_filename}' 时发生错误: {e}")
        # print("详细错误信息:")
        # traceback.print_exc()
        return False  # 表示处理失败


def process_pdf_directory(input_dir: Path, output_dir: Path):
    """
    处理指定目录下的所有 PDF 文件，并将结果保存到输出目录。

    Args:
        input_dir (Path): 包含 PDF 文件的输入目录 Path 对象。
        output_dir (Path): 保存处理后 PDF 文件的输出目录 Path 对象。
    """
    if not input_dir.is_dir():  # 使用 .is_dir() 方法
        print(f"错误：输入目录 '{input_dir}' 不存在或不是一个有效的目录。")
        return

    # 创建输出目录（如果不存在）
    output_dir.mkdir(parents=True, exist_ok=True)  # 使用 .mkdir()
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print("-" * 30)

    processed_count = 0
    skipped_count = 0
    error_count = 0

    # 遍历输入目录中的所有文件和子目录
    for item in input_dir.iterdir():  # 使用 .iterdir() 获取 Path 对象迭代器
        # 检查是否是 PDF 文件 (忽略大小写)
        if item.name.lower().endswith(".pdf"):  # 使用 .name 获取文件名字符串
            input_file_path = item  # item 本身就是 Path 对象

            # 只处理文件，不处理子目录
            if input_file_path.is_file():  # 使用 .is_file()
                print(f"正在处理: {input_file_path.name} ...")

                # 构建输出文件路径 (使用 / 操作符)
                output_file_path = output_dir / input_file_path.name

                # 调用处理函数
                success = add_filename_to_pdf(input_file_path, output_file_path)

                if success:
                    processed_count += 1
                    # 使用 .name 获取目录和文件名，更清晰地显示相对路径
                    print(f"  -> 已保存到: {output_dir.name}/{output_file_path.name}")
                else:
                    error_count += 1
            else:
                print(f"跳过: {item.name} (不是文件)")
                skipped_count += 1
        else:
            # 可选：打印跳过的非 PDF 文件信息
            # print(f"跳过: {item.name} (非 PDF 文件)")
            skipped_count += 1  # 可以选择是否统计非PDF文件的跳过

    print("-" * 30)
    print("处理完成。")
    print(f"成功处理文件数: {processed_count}")
    print(f"处理失败/跳过空文件数: {error_count}")
    # print(f"跳过非 PDF 或非文件数: {skipped_count}")


# --- 使用示例 ---
if __name__ == "__main__":
    # --- 确保输入目录存在 (如果不存在则创建并提示用户放入文件) ---
    if not INPUT_DIR.is_dir():
        print(f"输入目录 '{INPUT_DIR}' 不存在，已自动创建。")
        # 使用 .name 获取目录名用于提示
        print(
            f"请将需要处理的 PDF 文件放入 '{INPUT_DIR.name}' 文件夹中，然后重新运行脚本。"
        )
        INPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 创建一个示例文件，方便首次运行测试
        example_file_path = INPUT_DIR / "example.pdf"
        if not example_file_path.exists():  # 使用 .exists()
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter

                # reportlab 的 Canvas 可能仍需要字符串路径，使用 str() 转换
                c = canvas.Canvas(str(example_file_path), pagesize=letter)
                c.drawString(100, 750, "这是一个用于测试的 PDF 页面。")
                c.save()
                print(f"已在输入目录中创建示例文件 '{example_file_path.name}'")
            except ImportError:
                print("警告：未安装 reportlab，无法创建示例文件。")
            except Exception as e:
                print(f"创建示例文件时出错: {e}")
    else:
        # 如果输入目录存在，则执行处理
        process_pdf_directory(INPUT_DIR, OUTPUT_DIR)
