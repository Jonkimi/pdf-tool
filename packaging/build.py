import os
import sys
import subprocess
import shutil
from pathlib import Path

def build():
    """Build the application for the current platform."""
    print(f"Building for {sys.platform}...")
    
    # Ensure we are in the packaging directory or project root
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    spec_file = script_dir / "DocumentProcessor.spec"
    
    # Change to packaging directory for pyinstaller
    os.chdir(script_dir)
    print(f"Current working directory: {os.getcwd()}")
    
    if not spec_file.exists():
        print(f"Error: Spec file not found at {spec_file}")
        sys.exit(1)
    
    # Run PyInstaller
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        str(spec_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\nBuild successful!")
        dist_dir = script_dir / "dist"
        if sys.platform == "darwin":
            app_path = dist_dir / "DocumentProcessor.app"
            print(f"App bundle created at: {app_path}")
        else:
            exe_name = "DocumentProcessor.exe" if sys.platform == "win32" else "DocumentProcessor"
            exe_path = dist_dir / exe_name
            print(f"Executable created at: {exe_path}")
    else:
        print("\nBuild failed!")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
