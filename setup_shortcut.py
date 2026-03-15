"""One-click setup: generate app icon + create desktop shortcut.

Usage:
    .venv\\Scripts\\python.exe setup_shortcut.py
"""
import os
import sys
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(PROJECT_DIR, "assets", "app.ico")
VBS_PATH = os.path.join(PROJECT_DIR, "run.vbs")


def ensure_icon():
    if os.path.exists(ICON_PATH):
        print(f"[OK] Icon already exists: {ICON_PATH}")
        return
    print("[...] Generating app icon...")
    sys.path.insert(0, os.path.join(PROJECT_DIR, "assets"))
    from create_icon import create_icon
    create_icon()
    print(f"[OK] Icon generated: {ICON_PATH}")


def ensure_vbs():
    if os.path.exists(VBS_PATH):
        print(f"[OK] Launcher already exists: {VBS_PATH}")
        return
    print("[...] Creating run.vbs launcher...")
    content = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        'WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject")'
        ".GetParentFolderName(WScript.ScriptFullName)\n"
        'WshShell.Run """" & WshShell.CurrentDirectory & '
        '"\\.venv\\Scripts\\pythonw.exe"" """ & WshShell.CurrentDirectory & '
        '"\\main.py""", 0, False\n'
    )
    with open(VBS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Launcher created: {VBS_PATH}")


def create_desktop_shortcut():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "JP Assistant.lnk")

    ps_script = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$sc = $ws.CreateShortcut("{shortcut_path}"); '
        f'$sc.TargetPath = "wscript.exe"; '
        f'$sc.Arguments = """{VBS_PATH}"""; '
        f'$sc.WorkingDirectory = "{PROJECT_DIR}"; '
        f'$sc.IconLocation = "{ICON_PATH},0"; '
        f'$sc.Description = "JP Assistant - 日语学习助手"; '
        f'$sc.Save()'
    )

    result = subprocess.run(
        ["powershell", "-Command", ps_script],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"[OK] Desktop shortcut created: {shortcut_path}")
    else:
        print(f"[ERROR] Failed to create shortcut: {result.stderr}")
        return False
    return True


def main():
    print("=" * 50)
    print("  JP Assistant - Shortcut Setup")
    print("=" * 50)
    print()

    ensure_icon()
    ensure_vbs()

    print()
    create_desktop_shortcut()

    print()
    print("Done! Double-click 'JP Assistant' on your desktop to launch.")


if __name__ == "__main__":
    main()
