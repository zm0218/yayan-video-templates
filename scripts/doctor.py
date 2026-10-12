"""Read-only dependency and asset preflight; no install and no TTS request."""
import importlib.metadata
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.runtime import configure_console, load_catalog, resolve_runtime, run, select_template, verify_assets


def main():
    configure_console()
    runtime = resolve_runtime()
    print("PASS Node / Sharp / FFmpeg / FFprobe")
    for template in load_catalog()["templates"]:
        _, folder = select_template(template["id"])
        manifest = verify_assets(folder)
        print(f'PASS {template["id"]}: {len(manifest["files"])} 个资产哈希一致')
    print("PASS edge-tts " + importlib.metadata.version("edge-tts"))
    filters = run([runtime["ffmpeg"], "-hide_banner", "-filters"])
    encoders = run([runtime["ffmpeg"], "-hide_banner", "-encoders"])
    for name in ("loudnorm", "adelay", "apad", "atrim", "volumedetect"):
        if not re.search(r"\b" + name + r"\b", filters):
            raise RuntimeError("FFmpeg 缺少滤镜：" + name)
    for name in ("libx264", "aac", "pcm_s16le", "mjpeg"):
        if not re.search(r"\b" + name + r"\b", encoders):
            raise RuntimeError("FFmpeg 缺少编码器：" + name)
    print("PASS 必需滤镜与编码器")
    print("未联网试配音，未做画面/听感验收；环境检查不代表成片通过。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAIL " + str(exc), file=sys.stderr)
        sys.exit(1)
