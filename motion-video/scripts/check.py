import hashlib
import json
import math
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
# Provisional: half the weakest mock positive correlation. Recalibrate with real Gemini TTS.
VOICE_CORRELATION_THRESHOLD=0.499772
SILENCE_SECONDS=1.0

def cmd(args):
    p=subprocess.run(args,capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr.strip().split('\n')[-1])
    return p.stdout

def probe(path):
    return json.loads(cmd(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def read_audio(path):
    data=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','s16le','-ac','1','-ar','24000','pipe:1'],capture_output=True,check=True).stdout
    return np.frombuffer(data,dtype='<i2').astype(np.float64)/32768

def detect_silence(path, start, end):
    result=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af',f'atrim=start={start}:end={end},asetpts=PTS-STARTPTS,silencedetect=noise=-45dB:d={SILENCE_SECONDS}','-f','null','-'],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('silencedetect failed')
    return 'silence_start:' in result.stderr

def font_record(work):
    """Fonts the browser actually used (written by coverage.mjs). Never depends on OS font paths."""
    path=work/'platform_fonts.json'
    try: names=json.loads(path.read_text())
    except (OSError,ValueError): names=None
    if not isinstance(names,list) or not names: return {'status':'未記録','families':[]}
    return {'status':'記録済み','families':names}

def fingerprint(work):
    assets={}
    for path in sorted(work.iterdir()):
        if path.is_file() and path.name!='contact.png' and path.suffix.lower() in ('.html','.js','.png','.jpg','.jpeg','.webp','.svg'):
            assets[str(path.relative_to(work))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [ROOT/'runtime.js',ROOT/'scripts/scene3d.py']:
        assets[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    result={'effective_sha256':hashlib.sha256((work/'effective.json').read_bytes()).hexdigest(), 'browser':(work/'browser_version.txt').read_text().strip(), 'ffmpeg':cmd(['ffmpeg','-version']).splitlines()[0], 'assets':assets, 'fonts':font_record(work), 'blender':cmd(['blender','--version']).splitlines()[0] if json.loads((work/'effective.json').read_text()).get('threeD')=='blender' else None}
    (work/'render_env.json').write_text(json.dumps(result,indent=2))

def check(work):
    errors=[]
    browser_version=work/'browser_version.txt'
    browser=browser_version.read_text().strip() if browser_version.is_file() else None
    if browser is None or (browser!='synthetic-test' and not (work/'coverage_receipt.json').is_file()):
        print('FAIL coverage: not run (build did not finish coverage)')
        return 1
    tl=json.loads((work/'timeline.json').read_text()); video=work/'out.mp4'
    if browser!='synthetic-test':
        receipt=work/'coverage_receipt.json'
        got=json.loads(receipt.read_text())
        sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(work.iterdir()) if p.is_file() and p.name!='contact.png' and p.suffix.lower() in ('.html','.js','.png','.jpg','.jpeg','.webp','.svg')}
        expected={'effective':hashlib.sha256((work/'effective.json').read_bytes()).hexdigest(),'timeline':hashlib.sha256((work/'timeline.json').read_bytes()).hexdigest(),'sources':sources}
        if got!=expected:errors.append('coverage: scene changed since sweep')
    info=probe(video); streams=info['streams']; vs=next(s for s in streams if s['codec_type']=='video'); audio=next((s for s in streams if s['codec_type']=='audio'),None)
    frames=int(vs.get('nb_frames') or 0); expected=tl['total_frames']; seconds=expected/30
    if frames!=expected: errors.append(f'尺: frames {frames} != {expected}')
    if (int(vs['width']), int(vs['height'])) != (1920,1080): errors.append('尺: video size must be 1920x1080')
    if abs(float(info['format']['duration'])-seconds)>1/30+0.002: errors.append('尺: audio/video duration mismatch')
    if not 15<=seconds<=45: errors.append('総尺: outside 15-45s')
    if audio is None: errors.append('台詞ごとの声: audio stream absent')
    elif abs(float(audio.get('duration', 0))-seconds)>1/30+0.002: errors.append('尺: audio stream duration mismatch')
    else:
        correlations=[]
        mixed=read_audio(video); source=read_audio(work/'voice.wav')
        for i,line in enumerate(tl['lines']):
            reference=read_audio(line['wav']); start=(tl['intro_frames']+line['start'])*800
            left=max(0,start-1600);right=min(len(mixed),start+len(reference)+1601)
            window=mixed[left:right]
            fft_size=1 << (len(window)+len(reference)-2).bit_length()
            products=np.fft.irfft(np.fft.rfft(window,fft_size)*np.conj(np.fft.rfft(reference,fft_size)),fft_size)
            energy=np.concatenate(([0.0],np.cumsum(window*window)))
            positions=np.arange(max(0,start-1600-left),min(len(window)-len(reference),start+1600-left)+1)
            if len(positions):
                norms=np.sqrt(np.maximum(0,energy[positions+len(reference)]-energy[positions]))*np.linalg.norm(reference)
                corr=float(np.max(np.divide(products[positions],norms,out=np.zeros(len(positions)),where=norms>0)))
            else:corr=0.0
            correlations.append(corr)
            if corr<VOICE_CORRELATION_THRESHOLD: errors.append(f'台詞ごとの声[{i}]: correlation {corr:.3f} < {VOICE_CORRELATION_THRESHOLD}')
            segment=source[start:start+len(reference)]
            if len(segment)<len(reference): errors.append(f'無音[{i}]: voice.wav too short');continue
            segment_start=start/24000
            segment_end=(start+len(reference))/24000
            try:
                if detect_silence(work/'voice.wav',segment_start,segment_end):
                    errors.append(f'無音[{i}]: {SILENCE_SECONDS}s silence')
            except RuntimeError as exc:
                errors.append(f'無音[{i}]: {exc}')
    p=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-vf','blackdetect=d=0.5:pic_th=0.98:pix_th=0.02','-an','-f','null','-'],capture_output=True,text=True)
    for begin,end in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)',p.stderr):
        if float(end)>10/30 and float(begin)<seconds-10/30:errors.append(f'黒コマ: {begin}-{end}')
    fingerprint(work)
    try:
        thumbs=[]
        for at in (0.15,0.35,0.55,0.75,0.95):
            data=subprocess.run(['ffmpeg','-v','error','-ss',str(seconds*at),'-i',str(video),'-frames:v','1','-f','image2pipe','-vcodec','png','pipe:1'],capture_output=True,check=True).stdout
            import io
            im=Image.open(io.BytesIO(data)).convert('RGB');thumbs.append(ImageOps.fit(im,(384,216)))
        sheet=Image.new('RGB',(384*5,216));
        for i,im in enumerate(thumbs):sheet.paste(im,(384*i,0))
        sheet.save(work/'contact.png')
        review=work/'review';review.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vf',f'fps=1,scale=384:216,tile=5x{max(1,math.ceil(seconds/5))}', '-frames:v','1',str(review/'sheet.png')],check=True,capture_output=True)
    except Exception as exc:errors.append(f'contact sheet: {exc}')
    for error in errors:print('FAIL',error)
    if errors:return 1
    print(f'PASS 尺={seconds:.2f}s 台詞ごとの声={len(tl["lines"])} 相関最小={min(correlations):.6f} 無音=0 黒コマ=0 総尺=OK')
    return 0

if __name__=='__main__':sys.exit(check(Path(sys.argv[1])))
