import os
import tempfile
import zipfile
from pathlib import Path

from PIL import Image
from docx2pdf import convert  # Primary conversion method


# import subprocess # Keep commented out unless needed for alternative methods

# --- 配置 ---
INPUT_DIR = Path("./主体结构")  # 包含 Word 文件的输入目录
OUTPUT_DIR = Path("./output_pdfs")  # 保存 PDF 文件的输出目录
TEMP_DIR_BASE = Path("./temp_processing")  # 临时文件处理的根目录

# 图片压缩设置 ("最高级别 web 压缩" 的一种解释)
IMAGE_QUALITY = 75  # JPEG 压缩质量 (0-100, 较低=更高压缩/更低质量)
OPTIMIZE_PNG = True  # 是否优化 PNG 文件 (无损压缩)
# --- End Configuration ---


def compress_image_file(image_path, quality=75, optimize_png=True):
    """
    压缩单个图像文件。
    尝试就地修改文件。
    返回 True 表示成功压缩或优化, False 表示失败或跳过。
    """
    try:
        img = Image.open(image_path)
        original_format = img.format.upper() if img.format else None

        # Pillow 需要知道原始格式才能正确处理
        if original_format is None:
            # 尝试从文件扩展名猜测
            ext = image_path.suffix.lower()
            if ext == ".jpg":
                original_format = "JPEG"
            elif ext == ".png":
                original_format = "PNG"
            # 如果无法确定格式，则跳过
            else:
                print(
                    f"   Skipping compression (unknown original format): {image_path.name}"
                )
                img.close()
                return False

        print(f"   Processing image: {image_path.name} (Format: {original_format})")

        # 根据格式选择压缩策略
        if original_format in ["JPEG", "JPG"]:
            # 对于 JPEG，使用指定的质量重新保存
            # 确保颜色模式兼容 JPEG (e.g., convert RGBA to RGB)
            if img.mode == "RGBA":
                print(f"   Converting RGBA to RGB for JPEG: {image_path.name}")
                img = img.convert("RGB")
            img.save(
                image_path, "JPEG", quality=quality, optimize=True
            )  # optimize=True doesn't hurt JPEGs either
            print(f"   Compressed JPEG: {image_path.name} (Quality: {quality})")
            img.close()
            return True
        elif original_format == "PNG" and optimize_png:
            # 对于 PNG，如果启用，则进行优化
            img.save(image_path, "PNG", optimize=True)
            print(f"   Optimized PNG: {image_path.name}")
            img.close()
            return True
        # 可以添加对其他格式的处理，例如将 GIF/BMP/TIFF 转换为 JPEG 或 PNG
        # elif original_format in ["GIF", "BMP", "TIFF"]:
        #     target_format = "PNG" # or "JPEG"
        #     output_path = image_path.with_suffix(f".{target_format.lower()}")
        #     print(f"   Converting {original_format} to {target_format}: {image_path.name}")
        #     if img.mode == 'RGBA' and target_format == "JPEG":
        #         img = img.convert('RGB')
        #     img.save(output_path, target_format, quality=quality if target_format=="JPEG" else None, optimize=True if target_format=="PNG" else None)
        #     # Important: Need to update references in the docx XML if format/filename changes.
        #     # This adds complexity, so skipping conversion for now.
        #     print(f"   Skipping conversion for simplicity: {image_path.name}")
        #     img.close()
        #     return False # Indicate no in-place modification happened
        else:
            print(
                f"   Skipping compression (format not targeted or disabled): {image_path.name} ({original_format})"
            )
            img.close()
            return False  # No action taken

    except FileNotFoundError:
        print(f"   Error: Image file not found: {image_path}")
        return False
    except Exception as e:
        print(f"   Error compressing {image_path.name}: {e}")
        # Try to close the image object if it was opened
        try:
            img.close()
        except:
            pass
        return False


def process_word_document(docx_path, output_pdf_path, temp_dir_base):
    """
    处理单个 Word 文档：解压、压缩图片、重新打包、转换为 PDF。
    """
    print(f"\nProcessing: {docx_path.absolute()}")

    # 使用唯一的临时目录，并在完成后自动清理
    with tempfile.TemporaryDirectory(
        prefix=f"docx_{docx_path.stem}_", dir=temp_dir_base
    ) as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        extracted_path = temp_dir / "extracted"
        modified_docx_path = temp_dir / f"compressed_{docx_path.name}"

        try:
            # 1. 解压 .docx 文件
            print("  Extracting Word file...")
            with zipfile.ZipFile(docx_path, "r") as zip_ref:
                zip_ref.extractall(extracted_path)

            # 2. 查找并压缩 `word/media/` 中的图片
            media_path = extracted_path / "word" / "media"
            images_processed_count = 0
            if media_path.is_dir():
                print("  Compressing images in media folder...")
                for item in media_path.iterdir():
                    # 检查是否是支持压缩的文件类型
                    if item.is_file() and item.suffix.lower() in [
                        ".jpg",
                        ".jpeg",
                        ".png",
                    ]:  # Add other formats if handled by compress_image_file
                        if compress_image_file(
                            item, quality=IMAGE_QUALITY, optimize_png=OPTIMIZE_PNG
                        ):
                            images_processed_count += 1
            else:
                print("  No 'word/media' folder found.")

            if images_processed_count > 0:
                print(f"  Successfully processed {images_processed_count} images.")
                # 3. 如果有图片被修改，重新打包成新的 .docx 文件
                print("  Re-zipping processed Word file...")
                with zipfile.ZipFile(
                    modified_docx_path, "w", zipfile.ZIP_DEFLATED
                ) as zipf:
                    for root, _, files in os.walk(extracted_path):
                        arc_dir = Path(root).relative_to(extracted_path)
                        for file in files:
                            full_path = Path(root) / file
                            # 使用 as_posix() 确保 zip 文件内部路径使用 '/'
                            arc_name = (arc_dir / file).as_posix()
                            zipf.write(full_path, arcname=arc_name)
                source_docx_for_pdf = modified_docx_path
            else:
                print(
                    "  No images were compressed. Using original file for PDF conversion."
                )
                # 如果没有图片被处理，直接使用原始文件进行 PDF 转换
                source_docx_for_pdf = docx_path  # Use original docx path

            # 4. 将处理后（或原始）的 .docx 文件转换为 PDF
            print(
                f"  Converting '{source_docx_for_pdf.name}' to PDF -> '{output_pdf_path.name}'..."
            )
            try:
                # 确保输出 PDF 的目录存在
                output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

                # 使用 docx2pdf 进行转换
                convert(str(source_docx_for_pdf), str(output_pdf_path))

                # --- 可选：使用 LibreOffice 命令行 ---
                # soffice_path = "soffice" # 或提供完整路径 "C:\Program Files\LibreOffice\program\soffice.exe"
                # cmd = [
                #     soffice_path,
                #     "--headless",         # 无头模式运行
                #     "--convert-to", "pdf",# 转换目标格式为 pdf
                #     "--outdir", str(output_pdf_path.parent), # 指定输出目录
                #     str(source_docx_for_pdf) # 输入文件
                # ]
                # print(f"  Running command: {' '.join(cmd)}")
                # result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                # if result.returncode == 0 and output_pdf_path.exists():
                #      print(f"  Successfully created PDF via LibreOffice: {output_pdf_path.name}")
                # else:
                #     print(f"  LibreOffice conversion failed for {source_docx_for_pdf.name}:")
                #     print(f"  Return Code: {result.returncode}")
                #     print(f"  Stderr: {result.stderr}")
                #     print(f"  Stdout: {result.stdout}")
                #     # 可以考虑在此处引发异常或返回错误状态

                print(f"  Successfully created PDF: {output_pdf_path.absolute()}")

            except Exception as pdf_error:
                print(
                    f"  ERROR converting {source_docx_for_pdf.name} to PDF: {pdf_error}"
                )
                # 打印更详细的错误信息，尤其是 docx2pdf 可能的底层错误
                import traceback

                traceback.print_exc()

        except zipfile.BadZipFile:
            print(
                f"  ERROR: Invalid or corrupted Word file (not a zip archive): {docx_path.name}"
            )
        except Exception as e:
            print(f"  ERROR processing {docx_path.name}: {e}")
            import traceback

            traceback.print_exc()
        # finally:
        # tempfile.TemporaryDirectory 会自动清理，无需手动删除


def main():
    """
    主函数，执行整个流程。
    """
    print("Starting Word to PDF conversion with image compression...")
    print(f"Input directory:  {INPUT_DIR.resolve()}")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")
    print(f"Temp directory:   {TEMP_DIR_BASE.resolve()}")
    print(f"JPEG Quality:     {IMAGE_QUALITY}")
    print(f"Optimize PNGs:    {OPTIMIZE_PNG}")
    print("-" * 30)

    # 检查输入目录是否存在
    if not INPUT_DIR.is_dir():
        print(f"ERROR: Input directory '{INPUT_DIR}' not found.")
        return

    # 创建输出和临时目录（如果不存在）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR_BASE.mkdir(parents=True, exist_ok=True)

    # 查找所有 .docx 文件，排除临时文件
    docx_files = list(INPUT_DIR.rglob("*.docx"))
    valid_docx_files = [f for f in docx_files if not f.name.startswith("~$")]

    if not valid_docx_files:
        print("No valid .docx files found in the input directory.")
        return

    print(f"Found {len(valid_docx_files)} '.docx' files to process.")

    success_count = 0
    fail_count = 0

    for docx_path in valid_docx_files:
        try:
            # 计算输出 PDF 文件的路径，保留相对结构
            relative_path = docx_path.relative_to(INPUT_DIR)
            output_pdf_path = OUTPUT_DIR / relative_path.with_suffix(".pdf")

            # 处理单个文件
            process_word_document(docx_path, output_pdf_path, TEMP_DIR_BASE)
            # 假设如果 process_word_document 没有抛出严重错误并且 PDF 文件存在就是成功
            if output_pdf_path.exists():
                success_count += 1
            else:
                # 可能转换步骤失败但未抛出异常
                print(f"  WARNING: PDF file was not created for {docx_path.name}")
                fail_count += 1

        except Exception as e:
            print(f"FATAL ERROR processing file {docx_path.name}. Skipping. Error: {e}")
            fail_count += 1
            import traceback

            traceback.print_exc()

    print("-" * 30)
    print("Processing finished.")
    print(f"Successfully processed (PDF created): {success_count}")
    print(f"Failed or skipped: {fail_count}")
    # 可选：清理空的临时根目录，但通常保留它无害
    # try:
    #     if not any(TEMP_DIR_BASE.iterdir()):
    #         TEMP_DIR_BASE.rmdir()
    # except OSError:
    #     pass # Ignore if not empty or other error


if __name__ == "__main__":
    main()
