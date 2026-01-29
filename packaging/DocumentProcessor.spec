# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Base directory of the project
project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))

added_files = [
    (os.path.join(project_root, 'config'), 'config'),
    (os.path.join(project_root, 'document_processor_gui', 'resources'), os.path.join('document_processor_gui', 'resources')),
]

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    # macOS: Optimized for .app bundle (onedir mode)
    # This avoids the deprecation warning and is better for macOS security/performance.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='DocumentProcessor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='DocumentProcessor',
    )
    app = BUNDLE(
        coll,
        name='DocumentProcessor.app',
        icon=os.path.join(project_root, 'document_processor_gui', 'resources', 'app_icon.icns'),
        bundle_identifier='com.jonkimi.documentprocessor.gui',
    )
else:
    # Windows/Linux: Optimized for standalone executable (onefile mode)
    # Standalone binaries are easier to distribute on these platforms.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='DocumentProcessor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        # icon=os.path.join(project_root, 'icon.ico'), # Add icon if available
    )