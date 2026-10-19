const fs = require('fs');
const path = require('path');
const {spawn, spawnSync} = require('child_process');
const {once} = require('events');
const jobFile=path.resolve(process.argv[2]);
const job=JSON.parse(fs.readFileSync(jobFile));
const DIR=path.dirname(jobFile);
process.env.FONTCONFIG_FILE = path.join(DIR, 'fonts.conf');
const sharp = require(job.sharp);
sharp.cache(false);
sharp.concurrency(2);
const FFMPEG=job.ffmpeg, FFPROBE=job.ffprobe;
const W = 1920, H = 1080, FPS = 30;
const scenes = job.scenes;
const qa = path.join(DIR,'qa'), out = path.join(DIR,'renders');
const output = path.join(out,job.outputName);
const intermediate = path.join(DIR,'intermediate');
fs.mkdirSync(intermediate,{recursive:true});
const SILENT = path.join(intermediate,'picture.mp4');
const logo = job.logo, dsLogo=job.dsLogo;
const C={ink:'#0B1F4D',blue:'#263F94',navy:'#22217D',muted:'#5F6F89',light:'#E8F1FA'};
function run(bin,args) {
  const r=spawnSync(bin,args,{encoding:'utf8',maxBuffer:16*1024*1024});
  if(r.status!==0) throw new Error((r.stderr||r.stdout||'failed').slice(-5000));
  return r.stdout;
}
function duration(f) {return +run(FFPROBE,['-v','error','-show_entries','format=duration','-of','csv=p=0',f]).trim();}
function esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function svg(inner){return Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${inner}</svg>`);}
function text(x,y,t,size=40,fill=C.ink,weight=400,anchor='start') {return `<text x="${x}" y="${y}" font-family="Noto Sans CJK SC" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${esc(t)}</text>`;}
function rect(x,y,w,h,fill,rx=0){return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" rx="${rx}"/>`;}
function ease(n){n=Math.min(1,Math.max(0,n));return 1-Math.pow(1-n,3);}
function group(body,t,delay=0){const e=ease((t-delay)/.65);return `<g opacity="${e}" transform="translate(0,${(1-e)*22})">${body}</g>`;}
function width(t,size){return [...t].reduce((n,c)=>n+(/[a-zA-Z0-9 .×]/.test(c)?size*.55:size),0);}
function wrap(t,size,max){let out=[],line='';const units=t.match(/[^，。？！：、]+[，。？！：、]?/g)||[t];for(const unit of units){if(line&&width(line+unit,size)>max){out.push(line);line=unit;}else line+=unit;}if(line)out.push(line);return out;}
function stamp(sec){const ms=Math.round(sec*1000);return `${String(Math.floor(ms/3600000)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;}
async function imageAt(file,x,y,w,h,fit='contain',position='centre') {return {input:await sharp(file).rotate().flatten({background:'#FFFFFF'}).resize(w,h,{fit,position,background:'#FFFFFF'}).png().toBuffer(),left:x,top:y};}

async function buildBase(s){
 const base=sharp({create:{width:W,height:H,channels:3,background:'#F7FBFF'}});
 const layers=[];
 if(s.kind==='human'){
  layers.push(await imageAt(s.asset,0,150,1920,780,s.imageFit||'cover',s.imagePosition||'centre'));
  layers.push({input:svg(`<defs><linearGradient id="wash"><stop offset="0" stop-color="#F7FBFF"/><stop offset=".65" stop-color="#F7FBFF" stop-opacity=".94"/><stop offset="1" stop-color="#F7FBFF" stop-opacity="0"/></linearGradient></defs>${rect(0,150,1120,780,'url(#wash)')}`),left:0,top:0});
 } else if(s.kind==='screen'||s.kind==='product') {
  layers.push({input:svg(`${rect(765,213,1083,635,'#DFEAF6',30)}${rect(751,199,1083,635,'#FFFFFF',30)}`),left:0,top:0});
  layers.push(await imageAt(s.asset,777,226,1031,582,s.kind==='product'?'contain':'cover'));
 }
 const hero=s.kind==='partner'||s.kind==='closing';
 if(hero){
  layers.push({input:svg(`<defs><radialGradient id="g"><stop stop-color="#DBEEFF" stop-opacity=".7"/><stop offset="1" stop-color="#F7FBFF" stop-opacity="0"/></radialGradient></defs><ellipse cx="960" cy="590" rx="1050" ry="570" fill="url(#g)"/>${rect(0,160,1920,310,'#FFFFFF')}`),left:0,top:0});
  layers.push(await imageAt(logo,332,job.logoHasName?210:185,570,210));
  if(!job.logoHasName) layers.push({input:svg(text(617,447,job.clinicName,Math.min(35,710/width(job.clinicName,1)),job.headerNameColor||C.blue,700,'middle')),left:0,top:0});
  layers.push(await imageAt(dsLogo,1175,273,600,85));
 } else {
  layers.push({input:svg(rect(0,0,1920,155,'#FFFFFF')),left:0,top:0});
  layers.push(await imageAt(logo,72,17,358,121));
  if(!job.logoHasName){
   const meta=await sharp(logo).rotate().metadata();
   const logoWidth=Math.min(358,121*meta.width/meta.height);
   const nameX=Math.ceil(72+(358+logoWidth)/2+26);
   const nameSize=Math.min(42,Math.floor((1510-nameX)/width(job.clinicName,1)));
   layers.push({input:svg(text(nameX,77.5+nameSize*.36,job.clinicName,nameSize,job.headerNameColor||C.navy,700)),left:0,top:0});
  }
  layers.push(await imageAt(dsLogo,1440,54,390,55));
 }
 layers.push({input:svg(`${rect(0,928,1920,152,'#FFFFFF')}<line x1="80" y1="928" x2="1840" y2="928" stroke="#D5E3F2"/>`),left:0,top:0});
 return base.composite(layers).removeAlpha().raw().toBuffer();
}

function overlay(s,t,total){
 const hero=s.kind==='partner'||s.kind==='closing';
 const cues=s.cues, active=Math.max(0,cues.filter(c=>t>=c).length-1);
 let body='';
 const tc=s.titleCues;
 if(hero){
  body+=text(960,106,s.kind==='partner'?'合作升级 · 美白新体验':job.clinicName+' × HiTeeth 皓得适',Math.min(31,1720/width(job.clinicName+' × HiTeeth 皓得适',1)),C.muted,400,'middle');
  body+=group(text(960,334,'×',70,C.blue,400,'middle'),t,.1);
  body+=group(text(960,572,s.title[0],80,C.ink,700,'middle'),t,tc[0]);
  body+=group(text(960,677,s.title[1],s.kind==='closing'?66:80,C.blue,700,'middle'),t,tc[1]);
  if(s.kind==='partner'){
   let progress=Math.max(0,Math.min(1,(t-cues[0])/(cues[3]-cues[0]+1.8)));
   body+=`<line x1="414" y1="776" x2="1506" y2="776" stroke="#C7DDF2" stroke-width="3"/><line x1="414" y1="776" x2="${414+1092*progress}" y2="776" stroke="${C.blue}" stroke-width="4"/>`;
   s.tags.forEach((tag,i)=>{const x=414+i*364;const at=cues[i];body+=group(`<circle cx="${x}" cy="776" r="${i===active?16:12}" fill="${C.blue}" stroke="#F7FBFF" stroke-width="5"/>${text(x,840,tag,32,C.ink,700,'middle')}`,t,at);});
  }else{
   const at=cues[2];body+=group(`${rect(502,755,916,88,C.blue,44)}${text(960,812,s.tags[0],31,'#FFFFFF',400,'middle')}`,t,at);
   if(t>=at){const p=Math.min(1,(t-at)/(s.rawVoiceDuration+.4-at));body+=rect(555,856,810*p,4,C.blue,2);}
  }
 }else{
  const x=90;
  body+=group(text(x,284,s.eyebrow,Math.min(25,640/width(s.eyebrow,1)),C.blue,500),t,.1);
  body+=group(text(x,404,s.title[0],62,C.ink,700),t,tc[0]);
  body+=group(text(x,497,s.title[1],62,C.ink,700),t,tc[1]);
  body+=rect(x,544,126*ease((t-.7)/1.25),5,C.blue,2);
  s.tags.forEach((tag,i)=>{
   const y=623+i*64,at=s.kind==='service'?(s.rowReveal[i]-.35):cues[i];
   const selected=t>=cues[i]&&(i===cues.length-1||t<cues[i+1]);
   body+=group(`${selected?rect(88,y-40,Math.min(622,width(tag,29)+88),56,'#E7EDFF',12):''}<circle cx="107" cy="${y-10}" r="5" fill="${C.blue}"/>${text(132,y,tag,29,selected?C.blue:C.muted,selected?700:500)}`,t,at);
  });
  if(s.kind==='screen'||s.kind==='product')body+=text(1292,879,s.caption||'品牌素材演示',22,C.muted,400,'middle');
 }
 if(s.kind==='pathway'||s.kind==='service'){
  const rows=s.kind==='pathway'?[['01','日常护理','饮食与清洁，知道怎么做'],['02','复测牙色','了解变化，再讨论需求'],['03','按需维护','是否需要，由医生评估']]:[['评估与沟通','选择更清楚'],['产品与操作','过程有照顾'],['复测与维护','之后有指导']];
  body+=group(text(820,268,s.kind==='pathway'?'美白之后的三个关注点':'我们把服务做好 · 你把选择看清',30,C.blue,700),t,.1);
  rows.forEach((r,i)=>{const y=325+i*171,at=s.rowReveal?s.rowReveal[i]:cues[i],selected=t>=cues[i]&&(i===2||t<cues[i+1]);
   let v=rect(790,y,1025,141,selected?'#EAF0FF':'#FFFFFF',20);
   if(selected){const until=i<2?cues[i+1]:s.rawVoiceDuration+.4,p=Math.min(1,Math.max(0,(t-cues[i])/Math.max(.1,until-cues[i])));v+=rect(810,y+131,985*p,4,C.blue,2);}
   if(s.kind==='pathway')v+=`<circle cx="856" cy="${y+70}" r="32" fill="${selected?C.blue:'#EAF0FF'}"/>${text(856,y+82,r[0],29,selected?'#FFF':C.blue,700,'middle')}${text(922,y+57,r[1],38,C.ink,700)}${text(922,y+106,r[2],29,C.muted)}`;
   else v+=`${text(842,y+85,r[0],39,C.ink,700)}${text(1260,y+85,'→',42,C.blue)}${text(1370,y+85,r[1],38,C.blue,700)}`;
   body+=group(v,t,at);
  });
 }
 const c=s.captions.find(c=>t>=c.start&&t<c.end);
 if(c){const lines=wrap(c.text,39,1730);if(lines.length>2)throw new Error('caption overflow');lines.forEach((v,i)=>body+=text(960,lines.length===1?992:970+i*44,v,39,C.ink,500,'middle'));}
 body+=text(960,1050,'是否适合美白及具体方案，由医生评估；效果与感受因人而异。',21,C.muted,400,'middle');
 body+=rect(0,1075,1920,5,'#E2ECF7')+rect(0,1075,1920*(s.start+t)/total,5,C.blue);
 return svg(body);
}

async function frame(s,t,total){
 const layers=[];
 if(s.kind==='product'){
   // Keep genuine HD product photos static; switch cleanly at the narration cue.
   layers.push({input:s.productPanels[t<s.productSwitch?0:1],left:777,top:226});
 }
 layers.push({input:overlay(s,t,total)});
 return sharp(s.base,{raw:{width:W,height:H,channels:3}}).composite(layers).removeAlpha().raw().toBuffer();
}

async function main(){
 [logo,dsLogo,FFMPEG,FFPROBE,...scenes.filter(s=>s.asset).map(s=>s.asset)].forEach(f=>{if(!fs.existsSync(f))throw new Error('Missing '+f);});
 fs.mkdirSync(qa,{recursive:true});fs.mkdirSync(out,{recursive:true});
 const total=job.duration;
 if(!process.argv.includes('--stills')&&Math.abs(duration(path.join(DIR,'audio/narration.wav'))-total)>.03)throw new Error('Audio/video duration mismatch');
 for(const s of scenes){s.base=await buildBase(s);if(s.kind==='product'){s.productPanels=[];for(const f of [s.asset,s.product2])s.productPanels.push(await sharp(f).rotate().flatten({background:'#FFFFFF'}).resize(1032,582,{fit:'contain',background:'#FFFFFF',kernel:'lanczos3'}).png().toBuffer());}}
 const cards=[];
 for(const [i,s] of scenes.entries()){
  const raw=await frame(s,Math.min(4,s.seconds/2),total);
  const name=path.join(qa,`scene-${String(i+1).padStart(2,'0')}.png`);
  await sharp(raw,{raw:{width:W,height:H,channels:3}}).png().toFile(name);
  cards.push({input:await sharp(name).resize(640,360).png().toBuffer(),left:(i%2)*640,top:Math.floor(i/2)*360});
 }
 await sharp({create:{width:1280,height:Math.ceil(scenes.length/2)*360,channels:3,background:'#FFFFFF'}}).composite(cards).jpeg({quality:90}).toFile(path.join(qa,'contact-sheet.jpg'));
 for(const s of scenes.filter(s=>s.kind==='product')){
  for(const [name,t] of [['hp17',Math.min(2,s.productSwitch/2)],['hp30',Math.min(s.seconds-.1,s.productSwitch+1)]]){
   const raw=await frame(s,t,total);
   await sharp(raw,{raw:{width:W,height:H,channels:3}}).png().toFile(path.join(qa,`product-${name}.png`));
  }
 }
 console.log(JSON.stringify({duration:total,scenes:scenes.map(s=>({id:s.id,seconds:s.seconds})),output},null,2));
 if(process.argv.includes('--stills'))return;
 const ff=spawn(FFMPEG,['-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',`${W}x${H}`,'-r',String(FPS),'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',SILENT],{stdio:['pipe','ignore','pipe']});
 let err='';ff.stderr.on('data',c=>err+=c);ff.stdin.on('error',()=>{});
 const finished=new Promise((resolve,reject)=>{ff.on('error',reject);ff.on('close',c=>c===0?resolve():reject(new Error(err)));});
 for(const [i,s] of scenes.entries()){
  const count=Math.round(s.seconds*FPS);
  let prev=null;
  if(i>0)prev=await frame(scenes[i-1],scenes[i-1].seconds-.05,total);
  for(let n=0;n<count;n++){
   let raw=await frame(s,n/FPS,total);
   // Dissolve picture only; subtitle band switches cleanly to avoid double text.
   if(prev && n<10){const p=ease((n+1)/10);for(let k=0;k<W*928*3;k++)raw[k]=Math.round(raw[k]*p+prev[k]*(1-p));}
   if(!ff.stdin.write(raw))await once(ff.stdin,'drain');
  }
  console.log(`Rendered ${i+1}/${scenes.length}: ${s.id}`);
 }
 ff.stdin.end();await finished;
 if(process.argv.includes('--picture-only')){console.log('PICTURE_READY '+SILENT);return;}
 run(FFMPEG,['-y','-loglevel','error','-i',SILENT,'-i',path.join(DIR,'audio/narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t',String(total),'-movflags','+faststart',output]);
 fs.writeFileSync(path.join(qa,'media-info.json'),run(FFPROBE,['-v','error','-count_frames','-show_entries','format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,nb_read_frames,sample_rate,channels','-of','json',output]));
 run(FFMPEG,['-v','error','-i',output,'-f','null','-']);
 const vol=spawnSync(FFMPEG,['-i',output,'-af','volumedetect','-vn','-f','null','-'],{encoding:'utf8'});if(vol.status!==0)throw new Error(vol.stderr);
 fs.writeFileSync(path.join(qa,'audio-volume.txt'),vol.stderr);
 // Evidence is taken from the encoded delivery, independently of source-frame previews.
 for(const [i,s] of scenes.entries())run(FFMPEG,['-y','-loglevel','error','-ss',String(s.start+Math.min(4,s.seconds/2)),'-i',output,'-frames:v','1',path.join(qa,`final-${i+1}.jpg`)]);
 run(FFMPEG,['-y','-v','error','-i',output,'-ss',String(scenes.at(-1).start),'-t',String(scenes.at(-1).seconds),'-vn','-c:a','pcm_s16le',path.join(qa,'片尾试听.wav')]);
 fs.writeFileSync(path.join(qa,'checks.json'),JSON.stringify({decode:'passed',duration:duration(output),expectedDuration:total,clinic:job.clinicName,visualReview:'pending',listeningReview:'pending',status:'有旁白样片'},null,2));
 console.log('FINISHED '+output);
}
main().catch(e=>{console.error(e);process.exit(1);});
