from pathlib import Path
import json,re,math,sys
R=Path(sys.argv[1]).resolve().parent;J=json.loads((R/'job.json').read_text(encoding='utf-8'));S=J['scenes']
norm=lambda t:re.sub(r'[^\w\u4e00-\u9fff]','',t)
anchors={'opening':['拍照','自己是否','过程'],'partnership':['携手','诊间美白','后续维护','每一步'],'assessment':['牙色','敏感史','预期'],'comfort':['舒适化','选择方案','关注你的感受'],'record':['美白前','美白后','实际变化'],'maintenance':['饮食','牙色复测','是否需要'],'service':['选择更清楚','过程有照顾','之后有指导'],'benefits':['牙色','面对镜头','微笑'],'closing':['为每次微笑','做好准备','欢迎到院']}
for s in S:
 words=[json.loads(x) for x in (R/'audio'/f'{s["id"]}.jsonl').read_text(encoding='utf-8').splitlines()]
 clean=norm(s['text']);spoken=''.join(norm(w['text']) for w in words)
 assert spoken==clean,(s['id'],spoken,clean)
 chars=[]
 for w in words:
  z=norm(w['text']);chars.extend([{'start':.4+w['offset']/1e7,'end':.4+(w['offset']+w['duration'])/1e7}]*len(z))
 def at(a):
  i=clean.find(norm(a));assert i>=0,(s['id'],a);return round(chars[i]['start'],3)
 s['cues']=[at(a) for a in anchors[s['id']]]
 # Short phrases from the approved narration; timestamps come from the spoken words.
 units=re.findall(r'[^，。？！]+[，。？！]?',s['text']);groups=[];acc=''
 for u in units:
  if acc and len(norm(acc+u))>24:groups.append(acc);acc=''
  acc+=u
  if len(norm(acc))>=10 or u.endswith(('。','？','！')):groups.append(acc);acc=''
 if acc:
  if groups and len(norm(acc))<5:groups[-1]+=acc
  else:groups.append(acc)
 cursor=0;caps=[]
 for phrase in groups:
  n=len(norm(phrase));caps.append({'text':phrase,'start':round(chars[cursor]['start'],3),'end':round(chars[cursor+n-1]['end']+.10,3)});cursor+=n
 for a,b in zip(caps,caps[1:]):a['end']=min(b['start'],a['end'])
 s['captions']=caps
 if s['id']=='closing':s['titleCues']=s['cues'][:2]
 elif s['id']=='service':s['titleCues']=[.5,at('延伸到')];s['rowReveal']=[at('评估'),at('沟通'),at('维护')]
 else:s['titleCues']=[.25,.8]
 if s['id']=='comfort':s['productSwitch']=s['cues'][1]
(R/'job.json').write_text(json.dumps(J,ensure_ascii=False,indent=2),encoding='utf-8');(R/'story.json').write_text(json.dumps(S,ensure_ascii=False,indent=2),encoding='utf-8')
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
rows=[]
for s in S:
 for c in s['captions']:rows.append(f'{len(rows)+1}\n{stamp(s["start"]+c["start"])} --> {stamp(s["start"]+c["end"])}\n{c["text"]}')
(R/'source/旁白字幕.srt').write_text('\n\n'.join(rows),encoding='utf-8');print(json.dumps({'duration':J['duration'],'captions':len(rows),'timing':{s['id']:s.get('timingSource','word-boundaries') for s in S}},ensure_ascii=False))
for s in S:print(s['id'],s['cues'],[(c['start'],c['text']) for c in s['captions']])
