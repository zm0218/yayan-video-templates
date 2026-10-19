from pathlib import Path
import asyncio,json,subprocess,sys,math,wave,re
R=Path(sys.argv[1]).resolve().parent;J=json.loads((R/'job.json').read_text(encoding='utf-8'));S=J['scenes'];FF=J['ffmpeg'];PROBE=J['ffprobe']
async def generate(s):
 p=R/'audio'/f'{s["id"]}.mp3';txt=p.with_suffix('.txt');meta=p.with_suffix('.jsonl')
 if s.get('providedVoice'):
  p=Path(s['providedVoice'])
  d=float(subprocess.check_output([PROBE,'-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)]))
  if not math.isfinite(d) or d<.3:raise ValueError('导入的完整旁白时长无效：'+s['id'])
  # Imported audio has no speech alignment. Keep whole-scene audio and mark
  # proportional character timing explicitly; it requires human sync review.
  chars=re.sub(r'[^\w\u4e00-\u9fff]','',s['text']);unit=d*1e7/len(chars)
  words=[{'type':'WordBoundary','offset':round(i*unit),'duration':round(unit),'text':c} for i,c in enumerate(chars)]
  meta.write_text('\n'.join(json.dumps(w,ensure_ascii=False) for w in words),encoding='utf-8')
  s['timingSource']='estimated-from-whole-scene-audio'
  return d,p
 cached=p.exists() and meta.exists() and txt.exists() and txt.read_text(encoding='utf-8')==s['text']+'|rate=18'
 if not cached:
  if '--offline' in sys.argv:raise ValueError(f'{s["id"]} 的门诊名称旁白尚未缓存，需要联网生成。')
  import edge_tts
  tmp=p.with_name(p.stem+'.part.mp3');tm=meta.with_name(meta.stem+'.part.jsonl')
  print('更新门诊配音：'+s['id'],flush=True)
  try:
   await asyncio.wait_for(edge_tts.Communicate(s['text'],'zh-CN-XiaoxiaoNeural',rate='+18%',pitch='-1Hz',boundary='WordBoundary').save(str(tmp),str(tm)),timeout=90)
  except Exception as exc:
   raise RuntimeError('在线整段配音失败：'+s['id']+'。已保留缓存，可用相同参数 --resume 重试，或在新任务用 --voice-dir 导入两段完整旁白。') from exc
  tmp.replace(p);tm.replace(meta);txt.write_text(s['text']+'|rate=18',encoding='utf-8')
 dur=float(subprocess.check_output([PROBE,'-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)]))
 if not math.isfinite(dur) or dur<.3:raise ValueError('配音为空：'+s['id'])
 s['timingSource']='word-boundaries'
 return dur,p
async def main():
 frame=0;parts=[]
 for s in S:
  d,p=await generate(s);count=math.ceil((d+.85)*30)
  s.update(rawVoiceDuration=d,seconds=count/30,start=frame/30,end=(frame+count)/30);frame+=count;parts.append((s,p))
 total=frame/30;buf=bytearray(round(total*48000)*2)
 for s,p in parts:
  pcm=subprocess.check_output([FF,'-v','error','-i',str(p),'-ar','48000','-ac','1','-f','s16le','pipe:1']);pos=round((s['start']+.4)*48000)*2;buf[pos:pos+len(pcm)]=pcm
 with wave.open(str(R/'audio/raw.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(buf)
 subprocess.run([FF,'-y','-v','error','-i',str(R/'audio/raw.wav'),'-af','loudnorm=I=-18:TP=-1.5:LRA=7','-ar','48000','-ac','1',str(R/'audio/narration.wav')],check=True)
 J['duration']=total;(R/'job.json').write_text(json.dumps(J,ensure_ascii=False,indent=2),encoding='utf-8');(R/'story.json').write_text(json.dumps(S,ensure_ascii=False,indent=2),encoding='utf-8');print(f'配音已同步，总时长 {total:.2f} 秒',flush=True)
asyncio.run(main())
