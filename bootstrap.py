"""Explicit first-run setup. Install dependencies locally, never globally."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
from shared.runtime import ROOT, configure_console


def main():
    configure_console()
    if sys.version_info < (3, 10):
        raise RuntimeError("需要 Python 3.10 或以上；推荐 Python 3.12。")
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("请先安装 Node.js 22 LTS 或更新的 LTS（包含 npm），再运行本脚本。")
    version = subprocess.check_output([node, "--version"], text=True).strip().lstrip("v")
    if tuple(map(int, version.split(".")[:2])) < (20, 9):
        raise RuntimeError("Node.js 至少需要 20.9。")
    venv = ROOT / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True, cwd=ROOT)
    npm_args = [npm, "ci" if (ROOT / "package-lock.json").exists() else "install", "--no-fund", "--no-audit"]
    subprocess.run(npm_args, check=True, cwd=ROOT)
    subprocess.run([str(python), str(ROOT / "scripts/doctor.py")], check=True, cwd=ROOT)
    print("首次配置完成。后续使用：")
    print(f'"{python}" video.py --template ds-a --name "示例口腔" --logo "inputs/logo.png" --allow-online-tts')


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print("配置未完成：" + str(exc), file=sys.stderr)
        sys.exit(1)
