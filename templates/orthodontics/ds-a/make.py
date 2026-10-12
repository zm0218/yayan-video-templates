"""Clinic + DS reusable video. Only --name and --logo are required."""
import argparse, asyncio, datetime, hashlib, json, math, os, pathlib, re, shutil, subprocess, sys, wave
from xml.sax.saxutils import escape

T=pathlib.Path(__file__).resolve().parent
ROOT=T.parents[2]
sys.path.insert(0,str(ROOT))
from shared.runtime import configure_console, configure_fonts, resolve_runtime, verify_assets

def validate_name(name):
    name=name.strip()
    if not name or len(name)>32 or re.search(r'[\x00-\x1f\x7f{}<>:"/\\|?*]',name) or name.endswith('.'):
        raise ValueError('门诊名称须为1–32个字符，不能含控制字符、模板符号或文件名禁用字符 <>:"/\\|?*，不能以句点结尾。请确认可用于文件名的正式名称。')
    return name

def substitute(value,name):
    if isinstance(value,str):return value.replace('{{clinic_name}}',name)
    if isinstance(value,list):return [substitute(item,name) for item in value]
    if isinstance(value,dict):return {key:substitute(item,name) for key,item in value.items()}
    return value

def template_fingerprint():
    files=[T/name for name in ('make.py','render.cjs','story.template.json','assets/manifest.json')]
    files.append(ROOT/'shared/runtime.py')
    return hashlib.sha256(''.join(sha(file) for file in files).encode()).hexdigest()
def run(args):
    p=subprocess.run([str(a) for a in args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-4000:])
    return p.stdout
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def dump(path,value):pathlib.Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def timestamp(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

async def synthesize(scene,voice,folder):
    import edge_tts
    dest=folder/(scene['id']+'.mp3'); meta=folder/(scene['id']+'.json')
    request={'text':scene['spokenText'],**voice}
    key=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if dest.exists() and meta.exists():
        saved=json.loads(meta.read_text(encoding='utf-8'))
        if saved.get('requestKey')==key and saved.get('sha256')==sha(dest):return dest
    partial=dest.with_suffix('.partial'); boundaries=[]
    with partial.open('wb') as f:
        async for item in edge_tts.Communicate(scene['spokenText'],voice['name'],rate=voice['rate'],pitch=voice['pitch'],boundary='WordBoundary').stream():
            if item['type']=='audio':f.write(item['data'])
            else:boundaries.append(item)
    if partial.stat().st_size<1000:raise RuntimeError('空配音：'+scene['id'])
    partial.replace(dest)
    dump(meta,{'requestKey':key,'sha256':sha(dest),'displayText':scene['text'],'tts':request,'boundaries':boundaries,'wholeSceneTake':True})
    print('已生成整段旁白：'+scene['id'],flush=True)
    return dest

def main():
    configure_console()
    parser=argparse.ArgumentParser(description='DS模版A：门诊名称 + Logo → DeepSmile 合作升级横版有旁白样片')
    parser.add_argument('--name',required=True,help='门诊对外全称')
    parser.add_argument('--logo',required=True,help='本地 PNG/JPG/WebP/SVG Logo')
    parser.add_argument('--logo-has-name',action='store_true',help='Logo 本身已带门诊名称，页眉不再重复添加文字；制作前看图确认')
    parser.add_argument('--spoken-name',help='可选：门诊名称的配音读法，仅影响声音')
    parser.add_argument('--out',help='独立输出目录；默认自动生成新目录')
    parser.add_argument('--preview',action='store_true',help='只生成脚本和八张品牌替换预览，不联网、不生成 MP4')
    parser.add_argument('--resume',action='store_true',help='恢复同一个输出目录；输入不一致时拒绝恢复')
    parser.add_argument('--allow-online-tts',action='store_true',help='允许将门诊名称与三段公开文案发送至微软在线语音服务')
    parser.add_argument('--voice-dir',help='可选：使用本机三段完整旁白（understand/partnership/closing，mp3/wav/m4a），不请求在线语音')
    args=parser.parse_args()
    name=validate_name(args.name); spoken_name=(args.spoken_name or name).strip()
    if not spoken_name or len(spoken_name)>64 or re.search(r'[\x00-\x1f\x7f{}]',spoken_name):raise ValueError('配音名称格式无效。')
    if not args.preview and not args.voice_dir and not args.allow_online_tts:
        raise ValueError('本模板使用在线语音；获准发送门诊名称与三段公开文案后添加 --allow-online-tts。仅检查画面可使用 --preview。')
    logo=pathlib.Path(args.logo).expanduser().resolve()
    if not logo.is_file() or logo.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.svg'):raise ValueError('Logo 文件不存在或格式不支持。')
    runtime=resolve_runtime()
    ff,fp,node,sharp=[runtime[key] for key in ('ffmpeg','ffprobe','node','sharp')]
    run([node,'-e','const s=require(process.argv[1]);s(process.argv[2]).resize(2,2).png().toBuffer().then(()=>{}).catch(e=>{console.error("Logo 无法解码："+e.message);process.exit(1)})',sharp,logo])
    if not args.preview and not args.voice_dir:run([sys.executable,'-c','import edge_tts'])
    verify_assets(T)
    provided={}
    if args.voice_dir:
        voice_dir=pathlib.Path(args.voice_dir).expanduser().resolve()
        for scene_id in ('understand','partnership','closing'):
            candidates=[voice_dir/(scene_id+suffix) for suffix in ('.mp3','.wav','.m4a') if (voice_dir/(scene_id+suffix)).is_file()]
            if len(candidates)!=1:raise ValueError(f'本地旁白需为 {scene_id} 提供且只提供一个 mp3/wav/m4a 文件。')
            provided[scene_id]=candidates[0]
    out=pathlib.Path(args.out).expanduser().resolve() if args.out else ROOT/'output/ds-a'/f'job-{name}-{datetime.datetime.now():%Y%m%d-%H%M%S-%f}'
    # Never write into the reusable template itself.
    protected=[ROOT/p for p in ('templates','scripts','shared','docs','.git','node_modules','.venv')]
    if out==ROOT or any(out==p or p in out.parents for p in protected):raise ValueError('输出目录不能覆盖仓库根目录、源码或依赖；请使用 output/ 下的新目录。')
    request={'template':'ds-a','templateFingerprint':template_fingerprint(),'clinicName':name,'spokenName':spoken_name,'logoSHA256':sha(logo),'logoHasName':args.logo_has_name,'mode':'preview' if args.preview else 'video'}
    request['voiceSource']='provided' if provided else 'edge-tts'
    if provided:request['providedVoiceHashes']={key:sha(value) for key,value in provided.items()}
    if out.exists() and any(out.iterdir()):
        if not args.resume or not (out/'request.json').is_file() or json.loads((out/'request.json').read_text(encoding='utf-8'))!=request:
            raise ValueError('输出目录已有内容。请使用新目录；仅同一输入可用 --resume 恢复。')
    for folder in ('input','audio','qa','renders','intermediate','source'):(out/folder).mkdir(parents=True,exist_ok=True)
    dump(out/'request.json',request)
    print('本次任务目录：'+str(out),flush=True)
    clinic_logo=out/'input'/('clinic-logo-original'+logo.suffix.lower())
    if logo!=clinic_logo:shutil.copy2(logo,clinic_logo)
    if not (out/'source/template').exists():
        shutil.copytree(T,out/'source/template',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(ROOT/'shared',out/'source/shared',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    source=json.loads((T/'story.template.json').read_text(encoding='utf-8'))
    scenes=[]
    for s in source:
        scene=substitute(s,name)
        scene['asset']=str(T/scene['asset']) if scene.get('asset') else None
        text=substitute(s['text'],spoken_name).replace('DeepSmile','Deep Smile').replace('正畸','正基').replace('数智化','数质化')
        scene['spokenText']=text
        scenes.append(scene)
    voice={'name':'zh-CN-XiaoxiaoNeural','rate':'+29%','pitch':'+2Hz'}
    dynamics=[s for s in scenes if s['personalizedVoice']]
    if not args.preview and provided:
        for s in dynamics:
            original=provided[s['id']]
            dest=out/'audio'/(s['id']+'-provided'+original.suffix.lower())
            if original!=dest:shutil.copy2(original,dest)
            s['providedVoice']=str(dest)
            dump(out/'audio'/(s['id']+'.json'),{'source':'provided-whole-scene','sha256':sha(dest),'displayText':s['text'],'wholeSceneTake':True,'listeningReview':'pending'})
    elif not args.preview:
        async def generate():
            await asyncio.wait_for(asyncio.gather(*(synthesize(s,voice,out/'audio') for s in dynamics)),timeout=180)
        try:asyncio.run(generate())
        except Exception as exc:
            reason=f'{type(exc).__name__} HTTP {getattr(exc,"status","unknown")}'
            raise RuntimeError(f'在线配音失败（{reason}），已保留任务；检查网络/服务状态后用相同输入加 --out "{out}" --resume 重试。也可在新任务用 --voice-dir 导入获准的三段完整旁白，参见 docs/VOICE.md。') from exc
    cursor=0;frames=[];timing=[];srt=[]
    for index,s in enumerate(scenes):
        duration=s['seconds']; fitted=out/'audio'/(s['id']+'.wav')
        if not args.preview:
            if s['personalizedVoice']:
                raw=pathlib.Path(s['providedVoice']) if s.get('providedVoice') else out/'audio'/(s['id']+'.mp3')
                raw_duration=float(run([fp,'-v','error','-show_entries','format=duration','-of','csv=p=0',raw]))
                if not math.isfinite(raw_duration) or raw_duration<=0:raise ValueError('旁白时长无效：'+s['id'])
                duration=max(duration,math.ceil((raw_duration+.144+.12)*30)/30)
                run([ff,'-y','-v','error','-i',raw,'-af',f'loudnorm=I=-17:TP=-1.5:LRA=8,adelay=144,apad,atrim=0:{duration}','-ar','48000','-ac','1','-c:a','pcm_s16le',fitted])
                s['rawVoiceDuration']=raw_duration
            else:shutil.copy2(T/'assets/audio'/(s['id']+'.wav'),fitted)
            with wave.open(str(fitted),'rb') as w:
                if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(48000,1,2) or w.getnframes()!=round(duration*48000):raise ValueError('音频格式或时长异常：'+s['id'])
                frames.append(w.readframes(w.getnframes()))
        s.update(start=cursor,seconds=duration,end=cursor+duration)
        cursor+=duration;timing.append(s)
        srt.append(f'{index+1}\n{timestamp(s["start"]+.144)} --> {timestamp(s["end"]-.096)}\n{s["text"]}\n')
    if not args.preview:
        with wave.open(str(out/'audio/narration.wav'),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(b''.join(frames))
    (out/'source/旁白字幕.srt').write_text('\n'.join(srt),encoding='utf-8')
    dump(out/'story.json',timing)
    dump(out/'scene-timing.json',{'fps':30,'duration':cursor,'scenes':timing})
    configure_fonts(T,out)
    job={'template':'ds-a','clinicName':name,'logo':str(clinic_logo),'dsLogo':str(T/'assets/images/deepsmile-logo.png'),'sharp':sharp,'ffmpeg':ff,'ffprobe':fp,'duration':cursor,'outputName':f'DeepSmile-合作视频-{name}.mp4','scenes':timing,'previewOnly':args.preview}
    job['logoHasName']=args.logo_has_name
    dump(out/'job.json',job)
    print(f'共 8 个场景；预计时长 {cursor:.3f} 秒；输出：{out}',flush=True)
    result=subprocess.run([node,str(T/'render.cjs'),str(out/'job.json')]+(['--stills'] if args.preview else []))
    if result.returncode:raise RuntimeError('画面渲染失败，保留已生成配音；使用相同输入和 --resume 恢复。')
    dump(out/'delivery.json',{'template':'ds-a','request':request,'duration':cursor,'video':None if args.preview else str(out/'renders'/job['outputName']),'subtitle':str(out/'source/旁白字幕.srt'),'contactSheet':str(out/'qa/contact-sheet.jpg'),'voiceStatus':'preview-only' if args.preview else ('provided-whole-scene, listening-pending' if provided else 'whole-scene-generated, listening-pending'),'visualReview':'pending','fullPlaybackReview':'pending','listeningReview':'pending','status':'预览' if args.preview else '有旁白样片','previewOnly':args.preview})
    print('完成：'+str(out/'delivery.json'),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('停止：'+str(exc),file=sys.stderr);sys.exit(1)
