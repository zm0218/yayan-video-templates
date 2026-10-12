"""Resolve project dependencies without referring to the publisher's machine."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", **kwargs)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    return result.stdout


def configure_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_catalog():
    return json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def select_template(template_id):
    matches = [t for t in load_catalog()["templates"] if t["id"] == template_id]
    if len(matches) != 1:
        raise ValueError(f"找不到唯一模板 {template_id}；请先运行 python video.py --list")
    template = matches[0]
    folder = (ROOT / template["path"]).resolve()
    if ROOT not in folder.parents:
        raise ValueError("模板目录必须位于仓库内部")
    return template, folder


def verify_assets(folder):
    manifest = json.loads((folder / "assets/manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        file = (folder / item["path"]).resolve()
        if folder not in file.parents or not file.is_file() or sha(file) != item["sha256"]:
            raise ValueError("模板资产缺失或改变：" + item["path"])
    return manifest


def resolve_runtime():
    config_file = ROOT / "runtime.local.json"
    config = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
    node = os.environ.get("NODE_BIN") or config.get("node") or shutil.which("node")
    if not node:
        raise RuntimeError("缺少 Node.js。请安装 Node.js 22 LTS 或更新的 LTS，再运行 bootstrap.py。")
    version = run([node, "--version"]).strip().lstrip("v").split(".")
    if tuple(map(int, version[:2])) < (20, 9):
        raise RuntimeError("Node.js 至少需要 20.9；推荐 Node.js 22 LTS 或更新的 LTS。")
    sharp = os.environ.get("SHARP_MODULE") or config.get("sharp") or str(ROOT / "node_modules/sharp")
    run([node, "-e", "require(process.argv[1]);", sharp], cwd=ROOT)
    result = {"node": node, "sharp": sharp}
    for key in ("ffmpeg", "ffprobe"):
        candidate = os.environ.get(key.upper() + "_BIN") or config.get(key)
        if not candidate:
            try:
                candidate = run([node, "-e", "process.stdout.write(require(process.argv[1]).path)",
                                 f"@{key}-installer/{key}"], cwd=ROOT).strip()
            except RuntimeError:
                candidate = shutil.which(key)
        if not candidate:
            raise RuntimeError(f"缺少 {key}；请运行 bootstrap.py，或设置 {key.upper()}_BIN。")
        # Renderers expect a real path, also when an override uses a command name.
        candidate = shutil.which(candidate) or candidate
        run([candidate, "-version"])
        result[key] = str(Path(candidate).resolve())
    return result


def configure_fonts(folder, output):
    from xml.sax.saxutils import escape
    fonts = (folder / "assets/fonts").resolve().as_posix()
    cache = (output / ".fontcache").resolve().as_posix()
    config = output / "fonts.conf"
    config.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
                      f'<fontconfig><dir>{escape(fonts)}</dir><cachedir>{escape(cache)}</cachedir></fontconfig>',
                      encoding="utf-8")
    return config
