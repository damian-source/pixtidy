# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('ffmpeg-binaries/linux/ffprobe', 'ffmpeg-binaries/linux'), ('ffmpeg-binaries/macos/ffprobe', 'ffmpeg-binaries/macos'), ('ffmpeg-binaries/windows/ffprobe.exe', 'ffmpeg-binaries/windows'),('icon.ico', '.') ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PixTidy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='icon.ico'
)

