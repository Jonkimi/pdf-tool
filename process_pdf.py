import os
import platform
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# --- 配置 ---
INPUT_DIR = Path("./output_pdfs")  # 包含 PDF 文件的输入目录
OUTPUT_DIR = Path("./compressed_pdfs")  # 保存压缩后 PDF 的输出目录

# Ghostscript 压缩设置 (选择一个):
# /screen   - 最低质量，最小文件大小 (约 72 DPI 图像) - 适合屏幕查看
# /ebook    - 中等质量，较小文件大小 (约 150 DPI 图像) - 推荐的平衡点
# /printer  - 高质量，较大文件大小 (约 300 DPI 图像) - 适合打印
# /prepress - 非常高质量，文件大小可能更大 (约 300 DPI，颜色保留) - 用于专业打印
# /default  - Ghostscript 的默认设置，通常介于 ebook 和 printer 之间
COMPRESSION_LEVEL = "/screen"
# --- 新增：直接 DPI 控制 ---
TARGET_DPI = 144  # 设置目标图像分辨率 (例如 96, 130, 144, 150, 300)
DOWNSAMPLE_THRESHOLD = 1.1  # 设置下采样阈值 (1.0 表示只要图像分辨率 > TARGET_DPI 就进行下采样, 1.5 较宽松)
IMAGE_QUALITY = 75  # Add this: 1-100, lower means higher compression

# 如果遇到转换极慢 添加 -dHaveTransparency=false 或者在 Word 导出前就把复杂矢量图转为位图

# Ghostscript 可执行文件的路径
# 留空 '' 会尝试自动在 PATH 中查找
# 或者指定完整路径, 例如: r"C:\Program Files\gs\gs10.01.1\bin\gswin64c.exe"

GS_PATH = r"C:\Program Files\gs\gs10.05.0\bin\gswin64c.exe"
# --- End Configuration ---


def find_ghostscript():
    """尝试查找 Ghostscript 可执行文件。"""
    if GS_PATH and Path(GS_PATH).is_file():
        return GS_PATH

    system = platform.system()
    executable = None
    if system == "Windows":
        # 优先查找命令行版本 (gswinXc.exe)
        if shutil.which("gswin64c.exe"):
            executable = "gswin64c.exe"
        elif shutil.which("gswin32c.exe"):
            executable = "gswin32c.exe"
        # 备选 GUI 版本 (可能在某些系统 PATH 设置中优先)
        elif shutil.which("gswin64.exe"):
            executable = "gswin64.exe"
        elif shutil.which("gswin32.exe"):
            executable = "gswin32.exe"
    else:  # Linux/macOS
        executable = shutil.which("gs")

    if executable:
        print(f"找到 Ghostscript: {executable}")
        return executable
    else:
        print("错误：无法在系统 PATH 中找到 Ghostscript。")
        print("请安装 Ghostscript 并确保其 bin 目录在 PATH 环境变量中，")
        print("或者在脚本中设置 GS_PATH 为完整的可执行文件路径。")
        return None


def compress_pdf(input_pdf_path, output_pdf_path, gs_executable, level, target_dpi, threshold, image_quality=100):
    """使用 Ghostscript 压缩单个 PDF 文件。"""
    print(f"  正在压缩: {input_pdf_path.name} -> {output_pdf_path.name} (使用 {level})")

    # 确保输出目录存在
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建 Ghostscript 命令
    # 重要选项解释:
    # -sDEVICE=pdfwrite      : 指定输出设备为 PDF 写入器
    # -dCompatibilityLevel=1.4 : 设置 PDF 兼容性级别 (1.4 是个安全的选择)
    # -dPDFSETTINGS=...      : 设置预定义的压缩/质量级别 (来自配置)
    # -dNOPAUSE              : 处理完文件后不暂停
    # -dBATCH                : 处理完所有命令行指定的文件后退出 Ghostscript
    # -dQUIET                : 减少 Ghostscript 的输出信息 (可选, 便于查看脚本输出)
    # -sOutputFile=...       : 指定输出文件路径
    # input_pdf_path         : 输入文件路径
    cmd = [
        gs_executable,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.5",
        # f"-dPDFSETTINGS={level}",
        # --- 启用并设置 DPI 和阈值 ---
        # === 彩色图片 ===
        "-dDownsampleColorImages=true",
        "-dColorImageDownsampleType=/Bicubic",  # 添加：更好的缩放算法
        f"-dColorImageResolution={target_dpi}",
        f"-dColorImageDownsampleThreshold={threshold}",
        "-dAutoFilterColorImages=false",
        "-dColorImageFilter=/DCTEncode",
        "-dEncodeColorImages=true",
        "-dPassThroughJPEGImages=false",
        # === 灰度图片 ===
        "-dDownsampleGrayImages=true",
        "-dGrayImageDownsampleType=/Bicubic",
        f"-dGrayImageResolution={target_dpi}",
        f"-dGrayImageDownsampleThreshold={threshold}",
        "-dAutoFilterGrayImages=false",
        "-dGrayImageFilter=/DCTEncode",
        "-dEncodeGrayImages=true",
        # === 单色图片（特殊处理）===
        "-dDownsampleMonoImages=true",
        # "-dMonoImageDownsampleType=/Bicubic",
        # 单色图片用 /Subsample 更适合（边缘更锐利）
        "-dMonoImageDownsampleType=/Subsample",  # 而不是 /Bicubic
        f"-dMonoImageResolution={target_dpi * 2}",  # 单色需要更高 DPI
        f"-dMonoImageDownsampleThreshold={threshold}",
        # 不要对 Mono 用 DCTEncode！用默认的 CCITTFax 或 Flate
        "-dMonoImageFilter=/CCITTFaxEncode",
        "-dEncodeMonoImages=true",
        # === JPEG 质量 ===
        f"-dJPEGQ={image_quality}",
        # === 颜色优化 ===
        "-sColorConversionStrategy=RGB",
        "-dConvertCMYKImagesToRGB=true",
        "-sProcessColorModel=DeviceRGB",
        "-dOverrideICC=true",
        # === 字体处理（补充）===
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",  # 只嵌入用到的字符
        "-dCompressFonts=true",
        # === PDF 优化（补充）===
        "-dCompressStreams=true",  # 启用流压缩（1.5 核心）
        "-dCompressPages=true",  # 压缩页面描述
        "-dDetectDuplicateImages=true",  # 去重复图片
        "-dOptimize=true",  # 优化 PDF 结构
        "-dUseFlateCompression=true",  # 启用 Flate 无损压缩
        # === 网页优化 ===
        "-dFastWebView=true",  # 线性化，支持边下边看
        # --- 移除: -dPDFSETTINGS=... ---
        "-dNOPAUSE",
        "-dBATCH",
        "-dQUIET",  # 可以取消注释以查看更少的 GS 输出
        f"-sOutputFile={str(output_pdf_path)}",
        str(input_pdf_path),
    ]

    try:
        # 执行命令
        # capture_output=True 捕获 stdout 和 stderr
        # text=True 将捕获的输出解码为文本
        # check=False 不会在 GS 返回非零退出码时自动抛出异常，我们手动检查
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="ignore",
        )

        # 检查 Ghostscript 是否成功执行 (返回码 0 表示成功)
        if result.returncode == 0:
            print(f"  ✅ 成功压缩: {output_pdf_path.name}")
            # 可以比较文件大小 (可选)
            original_size = input_pdf_path.stat().st_size
            compressed_size = output_pdf_path.stat().st_size
            reduction = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
            print(
                f"     原始大小: {original_size / 1024:.1f} KB, 压缩后: {compressed_size / 1024:.1f} KB ({reduction:.1f}% 减小)"
            )
            return True
        else:
            print(f"  ❌ 压缩失败: {input_pdf_path.name}")
            print(f"     Ghostscript 返回代码: {result.returncode}")
            print(f"     错误信息 (stderr):\n{result.stderr}")
            # 如果压缩失败，删除可能产生的无效输出文件
            if output_pdf_path.exists():
                try:
                    output_pdf_path.unlink()
                except OSError as e:
                    print(f"     警告: 无法删除失败的输出文件 {output_pdf_path}: {e}")
            return False

    except FileNotFoundError:
        print(f"错误：无法执行 Ghostscript 命令。确认 '{gs_executable}' 路径正确且可用。")
        return False
    except Exception as e:
        print(f"执行 Ghostscript 时发生意外错误: {e}")
        return False


def _compress_pdf_worker(args):
    """多进程工作辅助函数。"""
    return compress_pdf(*args)


def main():
    """主函数，执行整个流程。"""
    print("开始 PDF 压缩流程...")
    print(f"输入目录: {INPUT_DIR.resolve()}")
    print(f"输出目录: {OUTPUT_DIR.resolve()}")
    print(f"压缩级别: {COMPRESSION_LEVEL}")

    # 检查输入目录
    if not INPUT_DIR.is_dir():
        print(f"错误: 输入目录 '{INPUT_DIR}' 不存在或不是一个目录。")
        return

    # 查找 Ghostscript
    gs_exe = find_ghostscript()
    if not gs_exe:
        return

    # 创建输出目录（如果不存在）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 查找所有 PDF 文件 (递归)
    pdf_files = list(INPUT_DIR.rglob("*.pdf"))

    if not pdf_files:
        print("在输入目录中未找到 PDF 文件。")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件，开始处理...")
    print("-" * 30)

    # success_count = 0
    # fail_count = 0

    # for pdf_path in pdf_files:
    #     print(f"\n处理文件: {pdf_path.relative_to(INPUT_DIR)}")

    #     # 计算输出 PDF 文件的路径，保留相对结构
    #     relative_path = pdf_path.relative_to(INPUT_DIR)
    #     output_pdf = OUTPUT_DIR / relative_path

    #     # 调用压缩函数
    #     if compress_pdf(
    #         pdf_path,
    #         output_pdf,
    #         gs_exe,
    #         COMPRESSION_LEVEL,
    #         TARGET_DPI,
    #         DOWNSAMPLE_THRESHOLD,
    #         IMAGE_QUALITY,
    #     ):
    #         success_count += 1
    #     else:
    #         fail_count += 1
    # 准备任务参数
    tasks = []
    for pdf_path in pdf_files:
        relative_path = pdf_path.relative_to(INPUT_DIR)
        output_pdf = OUTPUT_DIR / relative_path
        tasks.append(
            (
                pdf_path,
                output_pdf,
                gs_exe,
                COMPRESSION_LEVEL,
                TARGET_DPI,
                DOWNSAMPLE_THRESHOLD,
                IMAGE_QUALITY,
            )
        )
    num_workers = os.cpu_count()
    print(f"找到 {len(pdf_files)} 个文件，使用 {num_workers}个核心并行处理...")
    print("-" * 30)

    # 执行并行任务
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(_compress_pdf_worker, tasks))

        success_count = results.count(True)
        fail_count = results.count(False)

        print("-" * 30)
        print("处理完成。")
        print(f"成功压缩文件数: {success_count}")
        print(f"失败文件数: {fail_count}")
        print("-" * 30)


if __name__ == "__main__":
    main()
