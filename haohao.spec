"""Windows onedir release: immutable assets, Qt/ONNX/WinRT backends, app identity."""
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules, copy_metadata
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
)

root = Path(SPECPATH)
sys.path.insert(0, str(root))
from app_info import APP_NAME, APP_VERSION, ICON_PATH

version_numbers = tuple(int(v) for v in APP_VERSION.split(".")) + (0,)
version = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_numbers, prodvers=version_numbers, mask=0x3f,
                      flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable("080404b0", [
        StringStruct("FileDescription", APP_NAME),
        StringStruct("ProductName", APP_NAME),
        StringStruct("FileVersion", APP_VERSION),
        StringStruct("ProductVersion", APP_VERSION),
        StringStruct("OriginalFilename", f"{APP_NAME}.exe"),
    ])]), VarFileInfo([VarStruct("Translation", [2052, 1200])])],
)
metadata = []
for package in ("huggingface-hub", "meikiocr", "onnxruntime", "edge-tts"):
    metadata += copy_metadata(package)

a = Analysis(
    [str(root / "main.py")], pathex=[str(root)],
    binaries=[], datas=[(str(root / "assets" / "haohao.ico"), "assets"),
                        (str(root / "assets" / "sounds"), "assets/sounds")] + metadata,
    hiddenimports=collect_submodules("winrt") + collect_submodules("huggingface_hub"),
    hookspath=[], runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME,
          debug=False, strip=False, upx=False, console=False,
          icon=ICON_PATH, version=version)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=APP_NAME)
