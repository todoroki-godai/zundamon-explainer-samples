import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright-core';
import {renderFrame} from './render-frame.mjs';
import './coverage-logic.js';

const work=path.resolve(process.argv[2]);
const brief=JSON.parse(fs.readFileSync(path.join(work,'effective.json')));
const timeline=JSON.parse(fs.readFileSync(path.join(work,'timeline.json')));
const errors=[];
const fonts=new Set();
const pixelSamples=[];
const pixelFrames=[];
const browser=await chromium.launch({headless:true,channel:'chromium-headless-shell',args:['--disable-gpu','--font-render-hinting=none','--disable-partial-raster']});
try{
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 page.on('pageerror',error=>errors.push(`JS error: ${error.message}`));
 await page.route('**/*',route=>/^https?:/.test(route.request().url())?(errors.push('network request'),route.abort()):route.continue());
 await page.goto(pathToFileURL(path.join(work,'scene.html')).href);
 await page.addScriptTag({path:path.join(import.meta.dirname,'coverage-logic.js')});
 await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].filter(i=>i.src).map(i=>i.decode()));});
 await page.evaluate(data=>{window.motion=data;},{brief,timeline});
 const cdp=await page.context().newCDPSession(page);
 await cdp.send('DOM.enable');await cdp.send('CSS.enable');
 const render=frame=>renderFrame(page,frame);
 for(let frame=0;frame<timeline.main_frames;frame+=3){
  await render(frame);
  const front=frame%30===0?await page.screenshot({animations:'disabled'}):null;
  const {failures,candidates}=await page.evaluate(()=>{
   const errors=[],candidates=[];
   const colors=window.motion.brief.palette;
   const logic=window.motionCoverageLogic;
   const styleChain=el=>{const styles=[];for(let p=el;p;p=p.parentElement)styles.push(getComputedStyle(p));return styles;};
   const role=el=>el.classList.contains('em')?'em':el.classList.contains('t-on-bg')?'fg':el.classList.contains('t-on-surface')?'on-surface':'on-accent';
   const surface=el=>el.classList.contains('t-on-surface')?'surface':el.classList.contains('t-on-accent')?'accent':'bg';
   const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
   while(walk.nextNode()){
    const node=walk.currentNode,parent=node.parentElement;
    if(!node.textContent.trim()||parent.closest('script,style'))continue;
    if(!parent.closest('.t-on-bg,.t-on-surface,.t-on-accent,.em'))errors.push(`${parent.id||parent.tagName}: unclassified text`);
   }
   window.__coverageSeen??={};let elementIndex=0;
   for(const el of document.querySelectorAll('.t-on-bg,.t-on-surface,.t-on-accent,.em')){
    const key=String(elementIndex++);const seen=window.__coverageSeen[key]??={candidate:false,visible:false,opacitySamples:[],id:el.id||el.className};
    if(el.textContent.trim())seen.candidate=true;
    const id=el.id||el.className;
    if(el.classList.contains('em')&&!el.parentElement.closest('.t-on-bg'))errors.push(`${id}: em parent`);
    const style=getComputedStyle(el);
    const chain=styleChain(el);
    for(const s of chain){
     if(s.filter!=='none'||s.mixBlendMode!=='normal')errors.push(`${id}: filter or blend`);
    }
    if(chain.some(s=>s.display==='none'||s.visibility!=='visible'))continue;
    const opacity=logic.effectiveOpacity(chain);
    if(el.textContent.trim())seen.opacitySamples.push({own:Number(style.opacity),effective:opacity});
    const box=el.getBoundingClientRect();
    if(opacity<=.5)continue;
    if(el.textContent.trim())seen.visible=true;
    // Only frames readable at this sample receive the visual contract checks.
    if(!logic.sameOpaqueColor(style.color,colors[role(el)])||!logic.sameOpaqueColor(style.webkitTextFillColor,colors[role(el)]))errors.push(`${id}: text color contract`);
    let background,unsupportedBackground=false;
    for(let p=el;p;p=p.parentElement){const c=logic.parseRgb(getComputedStyle(p).backgroundColor);if(!c){unsupportedBackground=true;break;}if(c[3]>=.999){background=c;break;}}
    if(unsupportedBackground||!background||!logic.sameOpaqueColor(`rgb(${background.slice(0,3).join(',')})`,colors[surface(el)]))errors.push(`${id}: text surface contract`);
    if(box.left<-.5||box.top<-.5||box.right>1920.5||box.bottom>1080.5)errors.push(`${id}: viewport`);
    const dimensions=node=>({scrollWidth:node.scrollWidth,scrollHeight:node.scrollHeight,clientWidth:node.clientWidth,clientHeight:node.clientHeight});
    if(logic.hasInternalOverflow(dimensions(el))){
     // scrollWidth/scrollHeight also include transformed descendants. Measure the
     // same box without transforms to distinguish clipping from visual motion.
     const clone=el.cloneNode(true);
     clone.style.setProperty('position','fixed','important');
     clone.style.setProperty('left','-100000px','important');
     clone.style.setProperty('top','0','important');
     clone.style.setProperty('width',style.width,'important');
     clone.style.setProperty('height',style.height,'important');
     clone.style.setProperty('visibility','hidden','important');
     clone.style.setProperty('pointer-events','none','important');
     for(const node of [clone,...clone.querySelectorAll('*')])node.style.setProperty('transform','none','important');
     el.parentElement.appendChild(clone);
     try{if(logic.hasInternalOverflow(dimensions(clone)))errors.push(`${id}: internal overflow`);}
     finally{clone.remove();}
    }
    if(style.overflowX!=='visible'||style.overflowY!=='visible'||style.maxHeight!=='none')errors.push(`${id}: forbidden text clipping`);
    if(parseFloat(style.fontSize)<=0)errors.push(`${id}: hidden text`);
    for(let ancestor=el.parentElement;ancestor;ancestor=ancestor.parentElement){const st=getComputedStyle(ancestor),b=ancestor.getBoundingClientRect();if(st.overflow!=='visible'&&(box.left<b.left-.5||box.right>b.right+.5||box.top<b.top-.5||box.bottom>b.bottom+.5))errors.push(`${id}: ancestor clip`);if(st.clipPath!=='none'||st.maskImage!=='none')errors.push(`${id}: ancestor clip-path`);}
    if(el.textContent.trim()){
     if(box.width>1&&box.height>1)candidates.push({index:Number(key),id,clip:{x:Math.max(0,Math.floor(box.left)),y:Math.max(0,Math.floor(box.top)),width:Math.min(1920,Math.ceil(box.right))-Math.max(0,Math.floor(box.left)),height:Math.min(1080,Math.ceil(box.bottom))-Math.max(0,Math.floor(box.top))}});
    }
   }
   return {failures:[...new Set(errors)],candidates};
  });
  for(const failure of failures)errors.push(`frame ${frame}: ${failure}`);
  if(frame%30===0)pixelFrames.push({frame,candidates});
  if(frame%30===0){
   await render(Math.min(frame+15,timeline.main_frames-1));
   await render(frame);
   const back=await page.screenshot({animations:'disabled'});
   if(!front.equals(back)){
    const difference=await page.evaluate(async ([a,b])=>{
     const decode=async encoded=>{
      const bytes=Uint8Array.from(atob(encoded),char=>char.charCodeAt(0));
      return createImageBitmap(new Blob([bytes],{type:'image/png'}));
     };
     const [first,second]=await Promise.all([decode(a),decode(b)]);
     const canvas=document.createElement('canvas');canvas.width=first.width;canvas.height=first.height;
     const context=canvas.getContext('2d',{willReadFrequently:true});
     context.drawImage(first,0,0);const before=context.getImageData(0,0,canvas.width,canvas.height).data;
     context.clearRect(0,0,canvas.width,canvas.height);
     context.drawImage(second,0,0);const after=context.getImageData(0,0,canvas.width,canvas.height).data;
     let count=0,left=canvas.width,top=canvas.height,right=-1,bottom=-1;
     for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++){
      const i=(y*canvas.width+x)*4;
      if(before[i]===after[i]&&before[i+1]===after[i+1]&&before[i+2]===after[i+2]&&before[i+3]===after[i+3])continue;
      count++;left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);
     }
     first.close();second.close();
     return {count,bounds:count?`${left},${top}..${right},${bottom}`:'none'};
    },[front.toString('base64'),back.toString('base64')]);
    errors.push(`frame ${frame}: render order determinism (${difference.count} pixels, bounds ${difference.bounds})`);
   }
  }
  if(frame%30===0){
   const {root}=await cdp.send('DOM.getDocument');
   for(const selector of ['.t-on-bg','.t-on-surface','.t-on-accent','.em']){
    const {nodeIds}=await cdp.send('DOM.querySelectorAll',{nodeId:root.nodeId,selector});
    for(const nodeId of nodeIds){
     const result=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});
     for(const font of result.fonts)fonts.add(font.familyName);
    }
   }
  }
 }
 const pixelPage=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 pixelPage.on('pageerror',error=>errors.push(`JS error: ${error.message}`));
 await pixelPage.route('**/*',route=>/^https?:/.test(route.request().url())?(errors.push('network request'),route.abort()):route.continue());
 await pixelPage.goto(pathToFileURL(path.join(work,'scene.html')).href);
 await pixelPage.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].filter(i=>i.src).map(i=>i.decode()));});
 await pixelPage.evaluate(data=>{window.motion=data;},{brief,timeline});
 for(const {frame,candidates} of pixelFrames){
  await renderFrame(pixelPage,frame);
   for(const {index,id,clip} of candidates){
    if(clip.width<=0||clip.height<=0)continue;
    const ordinary=await pixelPage.screenshot({clip,animations:'disabled'});
    const prior=await pixelPage.evaluate(index=>{
     const element=document.querySelectorAll('.t-on-bg,.t-on-surface,.t-on-accent,.em')[index];
     const old=[element.style.getPropertyValue('visibility'),element.style.getPropertyPriority('visibility')];
     element.style.setProperty('visibility','hidden','important');return old;
    },index);
    let hidden;
    try{hidden=await pixelPage.screenshot({clip,animations:'disabled'});}
    finally{await pixelPage.evaluate(({index,prior})=>{
     const element=document.querySelectorAll('.t-on-bg,.t-on-surface,.t-on-accent,.em')[index];
     if(prior[0])element.style.setProperty('visibility',prior[0],prior[1]);else element.style.removeProperty('visibility');
    },{index,prior});}
    const changed=await pixelPage.evaluate(async ([a,b])=>{
     const decode=async encoded=>createImageBitmap(new Blob([Uint8Array.from(atob(encoded),char=>char.charCodeAt(0))],{type:'image/png'}));
     const [first,second]=await Promise.all([decode(a),decode(b)]);
     const canvas=document.createElement('canvas');canvas.width=first.width;canvas.height=first.height;
     const context=canvas.getContext('2d',{willReadFrequently:true});
     context.drawImage(first,0,0);const before=context.getImageData(0,0,canvas.width,canvas.height).data;
     context.clearRect(0,0,canvas.width,canvas.height);context.drawImage(second,0,0);
     const after=context.getImageData(0,0,canvas.width,canvas.height).data;
     let pixels=0;
     for(let i=0;i<before.length;i+=4)if(Math.max(Math.abs(before[i]-after[i]),Math.abs(before[i+1]-after[i+1]),Math.abs(before[i+2]-after[i+2]))>=8)pixels++;
     first.close();second.close();return {pixels,total:canvas.width*canvas.height};
    },[ordinary.toString('base64'),hidden.toString('base64')]);
    const fraction=changed.pixels/changed.total;
    pixelSamples.push({frame,id,fraction});
    if(globalThis.motionCoverageLogic.occludedFraction(fraction))errors.push(`frame ${frame}: ${id}: occluded text (${changed.pixels}/${changed.total} changed pixels)`);
   }
 }
 const {unread,opacityFailures}=await page.evaluate(()=>{
  const seen=Object.values(window.__coverageSeen||{});
  return {unread:seen.filter(item=>item.candidate&&!item.visible).map(item=>item.id),opacityFailures:seen.filter(item=>item.candidate&&window.motionCoverageLogic.opacityFailure(item.opacitySamples)).map(item=>item.id)};
 });
 for(const id of opacityFailures)errors.push(`${id}: opacity`);
 for(const id of unread)errors.push(`${id}: opacity or hidden text never readable`);
}finally{await browser.close();}
if(process.env.MOTION_VIDEO_PIXEL_DIAGNOSTICS==='1')console.error('PIXEL_MIN',JSON.stringify(pixelSamples.sort((a,b)=>a.fraction-b.fraction).slice(0,10)));
if(errors.length){for(const error of errors.slice(0,50))console.error('FAIL',error);process.exit(1);}
fs.writeFileSync(path.join(work,'platform_fonts.json'),JSON.stringify([...fonts].sort()));
const sources=Object.fromEntries(fs.readdirSync(work).filter(name=>name!=='contact.png'&&/\.(html|js|png|jpe?g|webp|svg)$/i.test(name)).sort().map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(work,name))).digest('hex')]));
fs.writeFileSync(path.join(work,'coverage_receipt.json'),JSON.stringify({effective:crypto.createHash('sha256').update(fs.readFileSync(path.join(work,'effective.json'))).digest('hex'),timeline:crypto.createHash('sha256').update(fs.readFileSync(path.join(work,'timeline.json'))).digest('hex'),sources}));
console.log(`PASS coverage ${timeline.main_frames} frames sampled every third frame; render order and fonts`);
