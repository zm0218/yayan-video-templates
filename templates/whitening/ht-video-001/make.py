"""HT视频001：门诊名称与 Logo → 皓得适合作视频。"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

T = Path(__file__).resolve().parent
ROOT = T.parents[2]
sys.path.insert(0, str(ROOT))
from shared.runtime import configure_console, configure_fonts, resolve_runtime, sha, verify_assets


def validate_name(name):
    name = name.strip()
    if not name or len(name) > 32 or re.search(r'[\x00-\x1f\x7f{}<>:"/\\|?*]', name) or name.endswith('.'):
        raise ValueError('门诊名称须为1–32个字符，不含控制字符、模板符号和文件名禁用字符，且不能以句点结尾。')
    return name


def substitute(value, name, logo):
    if isinstance(value, str):
        return value.replace('{{clinic_name}}', name).replace('{{clinic_logo}}', str(logo))
    if isinstance(value, list):
        return [substitute(v, name, logo) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, name, logo) for k, v in value.items()}
    return value


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def template_fingerprint():
    files = [T/'make.py', T/'template.json', T/'assets/manifest.json', ROOT/'shared/runtime.py']
    files.extend(sorted((T/'engine').glob('*.*')))
    return hashlib.sha256(''.join(sha(p) for p in files if p.is_file()).encode()).hexdigest()


def main():
    configure_console()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', required=True, help='门诊对外名称')
    p.add_argument('--logo', required=True, help='真实门诊 Logo 原图')
    p.add_argument('--logo-has-name', action='store_true', help='看过 Logo 后确认已含中文门诊名称')
    p.add_argument('--name-color', default='#263F94')
    p.add_argument('--out', '--output', dest='out', help='独立制作目录')
    p.add_argument('--preview', '--stills', dest='preview', action='store_true', help='离线生成九场景预览，不配音')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--offline', action='store_true', help='不请求在线配音；缺少缓存时停止')
    p.add_argument('--allow-online-tts', action='store_true', help='授权向微软发送本次门诊名称与公开宣传文案')
    p.add_argument('--voice-dir', help='导入 partnership 与 closing 两段完整旁白，支持 MP3/WAV/M4A')
    args = p.parse_args()
    name = validate_name(args.name)
    if not args.preview and not (args.allow_online_tts or args.voice_dir or args.offline):
        raise ValueError('本模板使用在线语音；已有授权请传 --allow-online-tts。也可 --preview 离线看图，或 --voice-dir 导入完整旁白。')
    logo = Path(args.logo).expanduser().resolve()
    if not logo.is_file() or logo.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.svg'):
        raise ValueError('Logo 文件不存在或格式不支持。')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', args.name_color):
        raise ValueError('名称颜色需为 #RRGGBB。')
    runtime = resolve_runtime()
    verify_assets(T)
    provided = {}
    if args.voice_dir:
        folder = Path(args.voice_dir).expanduser().resolve()
        for sid in ('partnership', 'closing'):
            files = [folder/(sid+ext) for ext in ('.mp3', '.wav', '.m4a') if (folder/(sid+ext)).is_file()]
            if len(files) != 1:
                raise ValueError(f'本地旁白需为 {sid} 提供且只提供一份 MP3/WAV/M4A，内容须与本次完整场景文案一致。')
            provided[sid] = files[0]
    out = Path(args.out).expanduser().resolve() if args.out else ROOT/'output/ht-video-001'/f'job-{name}-{datetime.datetime.now():%Y%m%d-%H%M%S-%f}'
    protected = [ROOT/d for d in ('templates', 'scripts', 'shared', 'tests', 'docs', '.github', '.git', 'node_modules', '.venv')]
    if out == ROOT or any(out == d or d in out.parents for d in protected):
        raise ValueError('输出目录不能覆盖仓库根目录、源码或依赖；请使用 output/ 下的新目录。')
    request = {'template': 'ht-video-001', 'templateName': 'HT视频001', 'templateFingerprint': template_fingerprint(),
               'clinicName': name, 'logoSHA256': sha(logo), 'logoHasName': args.logo_has_name,
               'nameColor': args.name_color, 'mode': 'preview' if args.preview else 'video',
               'voiceSource': 'provided' if provided else 'edge-tts',
               'providedVoiceHashes': {k: sha(v) for k, v in provided.items()}}
    if out.exists() and any(out.iterdir()):
        old = out/'request.json'
        if not args.resume or not old.is_file() or json.loads(old.read_text(encoding='utf-8')) != request:
            raise ValueError('输出目录已有内容；仅输入、模板指纹和模式一致时可用 --resume。否则请使用新目录。')
    for d in ('input', 'source', 'audio', 'qa', 'renders', 'intermediate'):
        (out/d).mkdir(parents=True, exist_ok=True)
    dump(out/'request.json', request)
    copied = out/'input'/('clinic-logo-original'+logo.suffix.lower())
    if logo != copied:
        shutil.copy2(logo, copied)
    if not (out/'source/template').exists():
        shutil.copytree(T, out/'source/template', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(ROOT/'shared', out/'source/shared', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    job = substitute(json.loads((T/'template.json').read_text(encoding='utf-8')), name, copied)
    job.update(logoHasName=args.logo_has_name, headerNameColor=args.name_color,
               outputName=f'HiTeeth皓得适-合作视频-{name}.mp4', **runtime)
    job['dsLogo'] = str(T/job['dsLogo'])
    for s in job['scenes']:
        for key in ('asset', 'product2', 'panel'):
            if key in s:
                s[key] = str(T/s[key])
        if s['id'] in provided:
            source = provided[s['id']]
            dest = out/'audio'/(s['id']+'-provided'+source.suffix.lower())
            if source != dest:
                shutil.copy2(source, dest)
            s['providedVoice'] = str(dest)
    for file in (T/'audio-cache').iterdir():
        if not (out/'audio'/file.name).exists():
            shutil.copy2(file, out/'audio'/file.name)
    dump(out/'job.json', job)
    configure_fonts(T, out)
    def run(*cmd):
        subprocess.run([str(x) for x in cmd], check=True, cwd=ROOT)
    print('本次任务目录：'+str(out), flush=True)
    if args.preview:
        run(runtime['node'], T/'engine/render.cjs', out/'job.json', '--stills')
    else:
        run(sys.executable, T/'engine/voice.py', out/'job.json',
            *(['--offline'] if args.offline or not args.allow_online_tts else []))
        run(sys.executable, T/'engine/schedule.py', out/'job.json')
        run(runtime['node'], T/'engine/render.cjs', out/'job.json', '--picture-only')
        run(sys.executable, T/'engine/deliver.py', out/'job.json')
    job = json.loads((out/'job.json').read_text(encoding='utf-8'))
    dump(out/'delivery.json', {'template': 'ht-video-001', 'templateName': 'HT视频001', 'request': request,
         'duration': job['duration'], 'video': None if args.preview else str(out/'renders'/job['outputName']),
         'subtitle': None if args.preview else str(out/'source/旁白字幕.srt'),
         'contactSheet': str(out/'qa/contact-sheet.jpg'), 'status': '预览' if args.preview else '有旁白样片',
         'voiceStatus': 'preview-only' if args.preview else ('provided-whole-scene, timing-review-pending' if provided else 'word-boundary-aligned, listening-pending'),
         'visualReview': 'pending', 'fullPlaybackReview': 'pending', 'listeningReview': 'pending',
         'previewOnly': args.preview})
    print('完成：'+str(out/'delivery.json'), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('停止：'+str(exc), file=sys.stderr)
        sys.exit(1)
