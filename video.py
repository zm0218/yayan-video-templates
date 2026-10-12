"""Single entry point; production always happens on this computer."""
import argparse
import subprocess
import sys
from shared.runtime import ROOT, configure_console, load_catalog, select_template


def main():
    configure_console()
    parser = argparse.ArgumentParser(description="牙颜视频模版库")
    parser.add_argument("--list", action="store_true", help="列出已收录模板")
    parser.add_argument("--template", help="模板编号，例如 ds-a")
    args, remaining = parser.parse_known_args()
    if args.list:
        for template in load_catalog()["templates"]:
            print(f'{template["id"]} | {template["name"]} | {template["description"]}')
        return 0
    if not args.template:
        parser.error("请指定 --template ds-a，或使用 --list 查看模板")
    template, folder = select_template(args.template)
    return subprocess.run([sys.executable, str(folder / template["entry"]), *remaining], cwd=ROOT).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError) as exc:
        print("停止：" + str(exc), file=sys.stderr)
        sys.exit(1)
