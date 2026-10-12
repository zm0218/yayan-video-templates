const fs = require('fs');
const path = require('path');
const {spawn, spawnSync} = require('child_process');
const {once} = require('events');
const jobFile=path.resolve(process.argv[2]);
const job=JSON.parse(fs.readFileSync(jobFile));
const DIR=path.dirname(jobFile);
process.env.FONTCONFIG_FILE = path.join(DIR, 'fonts.conf');
process.env.FONTCONFIG_PATH = DIR;
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
const C={ink:'#0B1F4D',blue:'#1769E8',navy:'#22217D',muted:'#5F6F89',light:'#E8F1FA'};
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
  layers.push(await imageAt(logo,250,189,735,248));
  layers.push(await imageAt(dsLogo,1205,261,475,110));
 } else {
  layers.push({input:svg(rect(0,0,1920,155,'#FFFFFF')),left:0,top:0});
  layers.push(await imageAt(logo,72,17,358,121));
  if(!job.logoHasName){
   const meta=await sharp(logo).rotate().metadata();
   const logoWidth=Math.min(358,121*meta.width/meta.height);
   const nameX=Math.ceil(72+(358+logoWidth)/2+26);
   const nameSize=Math.min(42,Math.floor((1510-nameX)/width(job.clinicName,1)));
   layers.push({input:svg(text(nameX,77.5+nameSize*.36,job.clinicName,nameSize,C.navy,700)),left:0,top:0});
  }
  layers.push(await imageAt(dsLogo,1610,53,222,57));
 }
 layers.push({input:svg(`${rect(0,928,1920,152,'#FFFFFF')}<line x1="80" y1="928" x2="1840" y2="928" stroke="#D5E3F2"/>`),left:0,top:0});
 return base.composite(layers).removeAlpha().raw().toBuffer();
}

function overlay(s,t,total){
 const actualTime=t;
 t*=1.25; // Retain the approved motion speed on the 64-second timeline.
 const hero=s.kind==='partner'||s.kind==='closing';
 let body='';
 if(hero){
  body+=text(960,106,s.kind==='partner'?'合作升级 · 正畸新体验':'让技术，成为你能感受到的服务',31,C.muted,400,'middle');
  body+=group(text(1080,334,'×',70,C.blue,400,'middle'),t,.1);
  body+=group(text(960,572,s.title[0],80,C.ink,700,'middle'),t,.28);
  body+=group(text(960,677,s.title[1],s.kind==='closing'?66:80,C.blue,700,'middle'),t,.5);
  if(s.kind==='partner'){
   const progress=ease((t-1.1)/2.6);
   body+=`<line x1="414" y1="776" x2="1506" y2="776" stroke="#C7DDF2" stroke-width="3"/><line x1="414" y1="776" x2="${414+1092*progress}" y2="776" stroke="${C.blue}" stroke-width="4"/>`;
   s.tags.forEach((tag,i)=>{const x=414+i*364;body+=group(`<circle cx="${x}" cy="776" r="13" fill="${C.blue}" stroke="#F7FBFF" stroke-width="5"/>${text(x,840,tag,32,C.ink,700,'middle')}`,t,1.1+i*.35);});
  } else {
   body+=group(`${rect(502,755,916,88,C.blue,44)}${text(960,812,s.tags[0],31,'#FFFFFF',400,'middle')}`,t,1.0);
  }
 }else{
  const x=90;
  const eyebrowSize=Math.min(25,Math.max(18,25*630/width(s.eyebrow,25)));
  const eyebrowLines=width(s.eyebrow,eyebrowSize)<=630?[s.eyebrow]:s.eyebrow.split(' · ');
  if(eyebrowLines.length>2||eyebrowLines.some(line=>width(line,eyebrowSize)>650))throw new Error('Clinic name too wide for opening label');
  eyebrowLines.forEach((line,i)=>body+=group(text(x,eyebrowLines.length===1?284:262+i*34,line,eyebrowSize,C.blue,500),t,.12));
  body+=group(text(x,404,s.title[0],s.kind==='human'?64:62,C.ink,700),t,.23);
  body+=group(text(x,497,s.title[1],s.kind==='human'?64:62,C.ink,700),t,.42);
  const line=ease((t-.7)/1.25);
  body+=`<rect x="${x}" y="544" width="${126*line}" height="5" rx="2" fill="${C.blue}"/>`;
  s.tags.forEach((tag,i)=>{
   const y=623+i*64;
   body+=group(`<circle cx="103" cy="${y-10}" r="5" fill="${C.blue}"/>${text(126,y,tag,29,C.muted,500)}`,t,.8+i*.2);
  });
  if(s.kind==='screen'||s.kind==='product')body+=group(text(1292,879,s.kind==='product'?'方案界面示意 · 不代表实际治疗结果':'情景演绎 · 界面示意',22,C.muted,400,'middle'),t,.65);
  else body+=text(1817,893,'AI 情景演绎',21,'#536B86',400,'end');
 }
 let subtitleSize=33,lines;
 for(;subtitleSize>=27;subtitleSize--){lines=wrap(s.text,subtitleSize,1730);if(lines.length<=2&&lines.every(line=>width(line,subtitleSize)<=1730))break;}
 if(subtitleSize<27)throw new Error('Subtitle overflow '+s.id);
 lines.forEach((line,i)=>body+=text(960,lines.length===1?981:970+i*42,line,subtitleSize,C.ink,400,'middle'));
 body+=text(960,1050,'AI 辅助分析与方案设计，诊疗决定由医生结合检查作出。',21,C.muted,400,'middle');
 body+=rect(0,1075,1920,5,'#E2ECF7')+rect(0,1075,1920*(s.start+actualTime)/total,5,C.blue);
 return svg(body);
}

async function frame(s,t,total){
 return sharp(s.base,{raw:{width:W,height:H,channels:3}}).composite([{input:overlay(s,t,total)}]).removeAlpha().raw().toBuffer();
}

async function main(){
 [logo,dsLogo,FFMPEG,FFPROBE,...scenes.filter(s=>s.asset).map(s=>s.asset)].forEach(f=>{if(!fs.existsSync(f))throw new Error('Missing '+f);});
 fs.mkdirSync(qa,{recursive:true});fs.mkdirSync(out,{recursive:true});
 const total=job.duration;
 if(!process.argv.includes('--stills')&&Math.abs(duration(path.join(DIR,'audio/narration.wav'))-total)>.03)throw new Error('Audio/video duration mismatch');
 for(const s of scenes)s.base=await buildBase(s);
 const cards=[];
 for(const [i,s] of scenes.entries()){
  const raw=await frame(s,Math.min(4,s.seconds/2),total);
  const name=path.join(qa,`scene-${String(i+1).padStart(2,'0')}.png`);
  await sharp(raw,{raw:{width:W,height:H,channels:3}}).png().toFile(name);
  cards.push({input:await sharp(name).resize(640,360).png().toBuffer(),left:(i%2)*640,top:Math.floor(i/2)*360});
 }
 await sharp({create:{width:1280,height:1440,channels:3,background:'#FFFFFF'}}).composite(cards).jpeg({quality:90}).toFile(path.join(qa,'contact-sheet.jpg'));
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
