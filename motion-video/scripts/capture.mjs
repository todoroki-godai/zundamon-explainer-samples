import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {chromium} from 'playwright-core';
import {renderFrame} from './render-frame.mjs';
const work=path.resolve(process.argv[2]);
const brief=JSON.parse(fs.readFileSync(path.join(work,'effective.json')));
const timeline=JSON.parse(fs.readFileSync(path.join(work,'timeline.json')));
const browser=await chromium.launch({headless:true,channel:'chromium-headless-shell',args:['--disable-gpu','--font-render-hinting=none','--disable-partial-raster']});
let blocked=[];
const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
await page.route('**/*',route=>{const url=route.request().url(); if (/^https?:/.test(url)){blocked.push(url); return route.abort();} return route.continue();});
const video=path.join(work,'main.mp4');
let ff;
try {
 await page.goto(pathToFileURL(path.join(work,'scene.html')).href);
 if(brief.image){
  const asset=path.resolve(work,brief.image);
  if(!asset.startsWith(work+path.sep)||!fs.existsSync(asset)||!fs.statSync(asset).isFile())throw Error('image must be a local workdir file');
 }
 await page.evaluate(async()=>{await document.fonts.ready; await Promise.all([...document.images].filter(img=>img.src).map(img=>img.decode()));});
 await page.evaluate(data=>{window.motion=data;},{brief,timeline});
 ff=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-f','image2pipe','-framerate','30','-vcodec','png','-i','pipe:0','-frames:v',String(timeline.main_frames),'-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-r','30',video],{stdio:['pipe','inherit','inherit']});
 const ffClosed=new Promise((resolve,reject)=>{ff.on('close',resolve);ff.on('error',reject);});
 for(let frame=0;frame<timeline.main_frames;frame++){
  await renderFrame(page,frame);
  if(blocked.length) throw Error('Network request blocked');
  const png=await page.screenshot({type:'png',animations:'disabled'});
  if(!ff.stdin.write(png)) await new Promise(r=>ff.stdin.once('drain',r));
 }
 ff.stdin.end();
 const code=await ffClosed; if(code!==0) throw Error(`ffmpeg exited ${code}`);
 if(blocked.length) throw Error('Network request blocked');
 fs.writeFileSync(path.join(work,'browser_version.txt'),browser.version());
} finally {if(ff && !ff.stdin.destroyed)ff.stdin.end(); await browser.close();}
