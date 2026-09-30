"""Deterministic four-on-the-floor/16-step synthesis from effective.json."""
import json
import re
import sys
import wave
from pathlib import Path
import numpy as np

SR=24000

def write_wav(path, samples):
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(SR)
        wav.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())

def frequency(note):
    match=re.fullmatch(r'([A-G])(#?)([0-8])',note)
    if not match: raise ValueError(f'invalid bass note: {note}')
    semitone={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[match[1]]+bool(match[2])
    midi=(int(match[3])+1)*12+semitone
    return 440*2**((midi-69)/12)

def synth(effective,frames):
    definition=effective['beatDefinition']; n=frames*800; audio=np.zeros(n,dtype=np.float64)
    if effective['beat']=='none': return audio
    rng=np.random.default_rng(effective['seed']); beat=60*SR/effective['bpm']; step=beat/4
    timbre=definition['timbre']; gains=timbre['gain']
    def add(samples,onset,gain):
        onset=int(round(onset)); end=min(n,onset+len(samples))
        if 0<=onset<end: audio[onset:end]+=samples[:end-onset]*gain
    def noise(length):return rng.standard_normal(length)
    for i in range(int(np.ceil(n/step))):
        onset=i*step+(definition['swing']*step if i%2 else 0)
        if onset>=n:break
        for kind,strengths in definition['steps'].items():
            strength=strengths[i%16]
            if not strength:continue
            length={'kick':.35,'snare':.17,'clap':.18,'hat':.06}[kind]
            t=np.arange(int(SR*length))/SR
            if kind=='kick':
                a,b=timbre['kick_pitch']; sample=np.sin(2*np.pi*(a+(b-a)*np.exp(-t*30))*t)*np.exp(-t*timbre['kick_decay'])
            elif kind=='snare':
                sample=(noise(len(t))*(1-timbre['snare_tone'])+np.sin(2*np.pi*180*t)*timbre['snare_tone'])*np.exp(-t*25)
            elif kind=='clap': sample=noise(len(t))*np.exp(-t*22)
            else:
                sample=noise(len(t));sample=np.diff(sample,prepend=0)*np.exp(-t*timbre['hat_decay'])
            add(sample,onset,strength*gains[kind])
    bass=definition['bass']; notes=bass['notes']
    if notes and bass['gain']:
        for bar in range(int(np.ceil(n/(beat*4)))):
            t=np.arange(int(SR*.5))/SR;phase=2*np.pi*frequency(notes[bar%len(notes)])*t
            wave={'sine':np.sin,'square':lambda x:np.sign(np.sin(x)),'triangle':lambda x:2/np.pi*np.arcsin(np.sin(x))}[bass['wave']](phase)
            add(wave*np.exp(-t*5),bar*beat*4,bass['gain'])
    if definition['riser']:
        length=min(n,3*SR)
        add(noise(length)*np.linspace(0,1,length)**2,0,.035)
    peak=float(np.max(np.abs(audio))) if len(audio) else 0
    if peak>1: raise ValueError(f'beat clipping before quantization: peak={peak:.3f}')
    if not np.any(audio): raise ValueError('beat unexpectedly silent')
    return audio

def run(work):
    effective=json.loads((work/'effective.json').read_text()); timeline=json.loads((work/'timeline.json').read_text())
    write_wav(work/'beat.wav',synth(effective,timeline['total_frames']))

if __name__=='__main__':run(Path(sys.argv[1]))
