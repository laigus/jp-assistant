"""Build and check the self-contained Windows release directory."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from app_info import APP_NAME, ICON_PATH
from app_paths import RESOURCE_DIR
from assets.create_icon import create_icon


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="Discard previous analysis cache")
    args = parser.parse_args()
    create_icon(ICON_PATH)
    env = os.environ.copy()
    # Do not collect unrelated native DLLs exposed by an IDE's expanded PATH.
    windows = Path(os.environ["WINDIR"])
    env["PATH"] = os.pathsep.join(map(str, (Path(sys.executable).parent, windows / "System32", windows)))
    env["PYTHONIOENCODING"] = "utf-8"
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if args.clean:
        command.append("--clean")
    subprocess.run(command + ["haohao.spec"], cwd=RESOURCE_DIR, env=env, check=True)
    executable = RESOURCE_DIR / "dist" / APP_NAME / f"{APP_NAME}.exe"
    env["QT_QPA_PLATFORM"] = "offscreen"
    checked = subprocess.run([str(executable), "--self-check"], env=env, timeout=60,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    if checked.returncode:
        raise RuntimeError(f"Release self-check failed ({checked.returncode}): {checked.stderr}")
    print(f"[OK] Release checked: {executable}")


if __name__ == "__main__":
    main()
