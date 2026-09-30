const textRoles=document.createElement('style');textRoles.textContent='.t-on-bg{color:var(--fg)}.t-on-surface{background:var(--surface);color:var(--on-surface)}.t-on-accent{background:var(--accent);color:var(--on-accent)}.em{color:var(--em)}';document.head.append(textRoles);
// Scene helpers. __render(frame) remains the workdir scene's entry point.
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const easeOut=x=>1-(1-clamp(x))**3;
function pulse(frame){const beat=60*window.motion.timeline.fps/window.motion.timeline.bpm;return Math.exp(-(frame%beat)/4);}
function transition(frame,start,end,span=8){return clamp((frame-start)/span)*(1-clamp((frame-(end-span))/span));}
function put(id,x,y,{s=1,r=0,o=1,center=true}={}){const el=document.getElementById(id);const px=center?x-el.offsetWidth/2:x,py=center?y-el.offsetHeight/2:y;el.style.transform=`translate(${px}px,${py}px) rotate(${r}deg) scale(${s})`;el.style.opacity=String(o);}
function drawMotif(frame){const motif=document.getElementById('motif');if(!motif)return;const p=window.motion.brief.palette;motif.className=p.motif;motif.style.opacity=String(p.motifOpacity);motif.style.transform=`translateX(${Math.sin(frame/120*Math.PI*2)*18}px)`;}
