from pathlib import Path
import json,subprocess,sys,re,hashlib,html
R=Path(sys.argv[1]).resolve().parent;J=json.loads((R/'job.json').read_text(encoding='utf-8'));S=J['scenes'];FF=J['ffmpeg'];PROBE=J['ffprobe'];O=R/'renders'/J['outputName']
def run(a):subprocess.run([FF,'-y','-v','error',*map(str,a)],check=True)
def probe(p):return json.loads(subprocess.check_output([PROBE,'-v','error','-count_frames','-show_entries','format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,sample_rate,channels','-of','json',str(p)]))
clips=[s for s in S if s.get('panel')]
for s in clips:
 d=float(probe(s['panel'])['format']['duration']);assert abs(d-s['seconds'])<.04,(s['id'],d,s['seconds'])
args=['-i',R/'intermediate/picture.mp4']
for s in clips:args+=['-i',s['panel']]
args+=['-i',R/'audio/narration.wav'];filters=[];prev='0:v'
for i,s in enumerate(clips,1):
 filters.append(f'[{i}:v]format=rgba,setpts=PTS+{s["start"]}/TB[p{i}]')
 filters.append(f'[{prev}][p{i}]overlay=x=777:y=226:eof_action=repeat:enable=\'gte(t,{s["start"]})*lt(t,{s["end"]})\'[v{i}]');prev=f'v{i}'
run(args+['-filter_complex',';'.join(filters),'-map',f'[{prev}]','-map',f'{len(clips)+1}:a','-t',J['duration'],'-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',O])
info=probe(O);(R/'qa/media-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');run(['-i',O,'-f','null','-'])
v=next(s for s in info['streams'] if s['codec_type']=='video');assert int(v['nb_read_frames'])==round(J['duration']*30)
assert any(s['codec_type']=='audio' for s in info['streams']);assert abs(float(info['format']['duration'])-J['duration'])<.04
norm=lambda t:re.sub(r'[^\w\u4e00-\u9fff]','',t)
for i,s in enumerate(S):
 assert norm(''.join(c['text'] for c in s['captions']))==norm(s['text'])
 assert all(c['start']<c['end']<=s['seconds'] for c in s['captions'])
 assert all(a['end']<=b['start'] for a,b in zip(s['captions'],s['captions'][1:]))
 for tag,dt in [('early',2),('late',s['seconds']-1.2)]:run(['-ss',s['start']+dt,'-i',O,'-frames:v','1',R/'qa'/f'final-{i+1:02}-{tag}.jpg'])
 if s.get('panel'):run(['-i',O,'-vf',f'select=eq(n\\,{round(s["end"]*30)-1})','-vsync','0','-frames:v','1',R/'qa'/f'lastframe-{s["id"]}.jpg'])
 if i:
  for tag,dt in [('before',-.1),('after',.25)]:run(['-ss',s['start']+dt,'-i',O,'-vf','scale=640:360','-frames:v','1',R/'qa'/f'cut-{i:02}-{tag}.jpg'])
product=next(s for s in S if s['kind']=='product');key=product['start']+product['productSwitch']+1
for t in [12,36,J['duration']-1,key]:run(['-ss',t,'-i',O,'-frames:v','1',R/'qa'/f'check-{t:.2f}s.jpg'])
partner=next(s for s in S if s['kind']=='partner');run(['-ss',partner['end']-1,'-i',O,'-frames:v','1',R/'qa/封面.jpg'])
vol=subprocess.run([FF,'-hide_banner','-i',str(O),'-af','volumedetect,silencedetect=n=-40dB:d=2','-vn','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True);(R/'qa/audio-analysis.txt').write_text(vol.stderr,encoding='utf-8')
checks={'clinicName':J['clinicName'],'logoHasName':J['logoHasName'],'outputSHA256':hashlib.sha256(O.read_bytes()).hexdigest(),'decode':'passed','duration':J['duration'],'frames':int(v['nb_read_frames']),'captionText':'complete and monotonic','crossCenterX':960,'visualReview':'pending','fullPlaybackReview':'pending','listeningReview':'pending','status':'有旁白审片版'}
checks['timingSources']={s['id']:s.get('timingSource','word-boundaries') for s in S}
(R/'qa/checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'播放视频.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(J['clinicName'])+' × 皓得适</title><style>body{margin:24px;background:#eff6fa;color:#263f94;font-family:system-ui}main{max-width:1200px;margin:auto}video{width:100%;background:white;border-radius:16px}</style><main><h1>'+html.escape(J['clinicName'])+' × 皓得适</h1><p>有旁白样片 · '+str(round(J['duration'],2))+' 秒</p><video controls preload="metadata" poster="qa/封面.jpg" src="renders/'+html.escape(J['outputName'],quote=True)+'"></video></main></html>',encoding='utf-8')
(R/'README.md').write_text(f'# {J["clinicName"]} × 皓得适\n\n成片：renders/{J["outputName"]}\n\n{J["duration"]:.2f} 秒；1920 × 1080；30 fps；H.264/AAC；中文旁白和字幕。\n\n已自动检查完整解码、帧数、音轨、字幕完整性和时间顺序。真实连续播放、主观听感和 Logo 目检需据实际审片补充，不以技术检查代替。导入的本地旁白使用估算字幕时间，须逐句复核同步。\n\n模板快照在 source/ 中；本工程仍引用仓库固定素材，移交工程时一并保留仓库。MP4 可单独发送。\n',encoding='utf-8')
print('导出与自动检查完成：'+str(O),flush=True)
