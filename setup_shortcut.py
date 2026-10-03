"""Build the application icon and install its desktop shortcut.

Usage:
    .venv\\Scripts\\python.exe setup_shortcut.py
"""
import os
import sys
import subprocess

from app_info import APP_NAME, BASE_DIR, ICON_PATH
from assets.create_icon import create_icon

PROJECT_DIR = str(BASE_DIR)
VBS_PATH = os.path.join(PROJECT_DIR, "run.vbs")


def ensure_icon():
    create_icon(ICON_PATH)
    print(f"[OK] Icon updated: {ICON_PATH}")


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
    env = os.environ.copy()
    env.update(APP_SHORTCUT_NAME=APP_NAME, APP_LAUNCHER_PATH=VBS_PATH,
               APP_PROJECT_DIR=PROJECT_DIR, APP_ICON_PATH=ICON_PATH)
    # Pass values as data, not interpolated PowerShell source.
    ps_script = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop ($env:APP_SHORTCUT_NAME + '.lnk')
$arguments = '"' + $env:APP_LAUNCHER_PATH + '"'
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = Join-Path $env:WINDIR 'System32/wscript.exe'
$sc.Arguments = $arguments
$sc.WorkingDirectory = $env:APP_PROJECT_DIR
$sc.IconLocation = $env:APP_ICON_PATH + ',0'
$sc.Description = $env:APP_SHORTCUT_NAME
$sc.Save()
$saved = $ws.CreateShortcut($shortcutPath)
if ($saved.Arguments -ne $arguments -or $saved.IconLocation -ne ($env:APP_ICON_PATH + ',0') -or
    $saved.WorkingDirectory -ne $env:APP_PROJECT_DIR -or
    [IO.Path]::GetFileName($saved.TargetPath) -ine 'wscript.exe') {
    throw 'Shortcut verification failed'
}
# Remove only duplicate shortcuts that launch this exact project.
foreach ($candidate in Get-ChildItem -LiteralPath $desktop -Filter '*.lnk' -File) {
    if ($candidate.FullName -eq $shortcutPath) { continue }
    try { $old = $ws.CreateShortcut($candidate.FullName) } catch { continue }
    if ($old.Arguments -eq $arguments -and [IO.Path]::GetFileName($old.TargetPath) -ieq 'wscript.exe') {
        Remove-Item -LiteralPath $candidate.FullName
    }
}
Write-Output $shortcutPath
'''
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    if result.returncode:
        raise RuntimeError(f"Desktop shortcut setup failed: {result.stderr.strip()}")
    shortcut_path = result.stdout.strip()
    print(f"[OK] Desktop shortcut updated: {shortcut_path}")
    return shortcut_path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"{APP_NAME} - Shortcut Setup")
    ensure_icon()
    ensure_vbs()
    create_desktop_shortcut()
    print(f"Done! Double-click '{APP_NAME}' on your desktop to launch.")


if __name__ == "__main__":
    main()
