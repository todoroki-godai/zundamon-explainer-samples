import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from beat import write_wav

def run(args): subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

def main(work):
    tl=json.loads((work/'timeline.json').read_text()); n=tl['total_frames']*800
    voice=np.zeros(n,dtype=np.float64)
    for line in tl['lines']:
        with wave.open(line['wav']) as wav:
            samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float64)/32768
        start=(tl['intro_frames']+line['start'])*800
        voice[start:start+len(samples)]+=samples[:max(0,n-start)]
    write_wav(work/'voice.wav',voice)
    if tl['intro_frames']:
        frames=sorted((work/'intro').glob('*.png'))
        if len(frames)!=90 or [p.name for p in frames]!=[f'{i:05d}.png' for i in range(90)]: raise ValueError('Blender intro requires exactly 90 numbered PNG frames')
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','30','-i',str(work/'intro/%05d.png'),'-frames:v','90','-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(work/'intro.mp4')])
        (work/'concat.txt').write_text("file 'intro.mp4'\nfile 'main.mp4'\n")
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(work/'video.mp4')])
        video=work/'video.mp4'
    else: video=work/'main.mp4'
    # Voice stays prominent; a fixed linear mix and limiter makes detection reproducible.
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),'-i',str(work/'voice.wav'),'-i',str(work/'beat.wav'),'-filter_complex','[1:a]volume=1.0[v];[2:a]volume=0.18[b];[v][b]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9,loudnorm=I=-14:TP=-1.5:LRA=11[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','24000','-ac','1','-t',str(tl['total_frames']/30),'-metadata','creation_time=','-metadata','encoder=','-movflags','+faststart',str(work/'out.mp4')])

if __name__=='__main__':main(Path(sys.argv[1]))
