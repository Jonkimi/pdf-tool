import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image

def generate_icns():
    print("Starting ICNS generation...")
    
    # Paths
    project_root = Path(__file__).parent.parent
    resources_dir = project_root / 'document_processor_gui' / 'resources'
    source_icon = resources_dir / 'app_icon.png'
    iconset_dir = resources_dir / 'app_icon.iconset'
    dest_icns = resources_dir / 'app_icon.icns'
    
    if not source_icon.exists():
        print(f"Error: Source icon not found at {source_icon}")
        return

    # Create iconset directory
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Created iconset directory: {iconset_dir}")

    # Open source image
    img = Image.open(source_icon)
    
    # Sizes required for macOS iconset
    sizes = [
        (16, 1, 'icon_16x16.png'),
        (16, 2, 'icon_16x16@2x.png'),
        (32, 1, 'icon_32x32.png'),
        (32, 2, 'icon_32x32@2x.png'),
        (128, 1, 'icon_128x128.png'),
        (128, 2, 'icon_128x128@2x.png'),
        (256, 1, 'icon_256x256.png'),
        (256, 2, 'icon_256x256@2x.png'),
        (512, 1, 'icon_512x512.png'),
        (512, 2, 'icon_512x512@2x.png'),
    ]
    
    # Generate resized images
    for size, scale, filename in sizes:
        pixel_size = size * scale
        print(f"Generating {filename} ({pixel_size}x{pixel_size})...")
        resized_img = img.resize((pixel_size, pixel_size), Image.Resampling.LANCZOS)
        resized_img.save(iconset_dir / filename)

    # Run iconutil
    print("Running iconutil...")
    cmd = ['iconutil', '-c', 'icns', str(iconset_dir), '-o', str(dest_icns)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Successfully generated: {dest_icns}")
        # Cleanup
        shutil.rmtree(iconset_dir)
        print("Cleaned up iconset directory.")
    else:
        print("Error running iconutil:")
        print(result.stderr)

if __name__ == "__main__":
    generate_icns()
