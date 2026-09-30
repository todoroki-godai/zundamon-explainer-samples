"""Resolve the four named axes once, before any build stage runs."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('announce', 'study', 'cm', 'chart', 'flyer', 'story', 'history', 'profile')
VOICES = ('Puck', 'Kore', 'Charon', 'Aoede', 'Leda', 'Fenrir', 'Zephyr', 'Orus')

def preset(axis, name):
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(f'invalid {axis} preset: {name}')
    path = ROOT / 'presets' / axis / f'{name}.json'
    if not path.is_file():
        raise ValueError(f'unknown {axis} preset: {name}')
    return json.loads(path.read_text())

def rgb(s):
    if not isinstance(s, str) or len(s) != 7 or s[0] != '#':
        raise ValueError(f'invalid color: {s}')
    try: return tuple(int(s[i:i+2], 16)/255 for i in (1,3,5))
    except ValueError: raise ValueError(f'invalid color: {s}') from None

def luminance(s):
    return sum(k*(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4) for k,v in zip((.2126,.7152,.0722),rgb(s)))

def ratio(a,b):
    x,y=sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)

def blended(a,b,opacity):
    values=[round((x*opacity+y*(1-opacity))*255) for x,y in zip(rgb(a),rgb(b))]
    return '#'+''.join(f'{n:02x}' for n in values)

def validate_theme(theme):
    for key in ('bg','fg','surface','on-surface','accent','on-accent','em','accent2','warn'):
        rgb(theme[key])
    opacity=theme.get('motifOpacity',0)
    if not 0 <= opacity <= .25: raise ValueError('motif opacity must be <= 0.25')
    for text,bg in (('fg','bg'),('on-surface','surface'),('on-accent','accent'),('em','bg')):
        if ratio(theme[text],theme[bg]) < 4.5:
            raise ValueError(f'contrast {text}/{bg} below 4.5')
    for text in ('fg','em'):
        if ratio(theme[text],blended(theme['accent2'],theme['bg'],opacity)) < 4.5:
            raise ValueError(f'contrast {text}/motif below 4.5')

def validate_beat(beat):
    def number(value, lo, hi, label):
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'beat {label} outside {lo}..{hi}')
    number(beat['bpm'],40,240,'bpm'); number(beat['swing'],0,.5,'swing')
    for key in ('kick','snare','clap','hat'):
        steps=beat['steps'][key]
        if len(steps)!=16: raise ValueError(f'beat {key} requires 16 steps')
        for n in steps: number(n,0,1,key)
    bass=beat['bass']; number(bass['gain'],0,1,'bass.gain')
    if bass['wave'] not in ('square','sine','triangle'): raise ValueError('invalid bass wave')
    for note in bass['notes']:
        if not isinstance(note,str) or len(note)<2 or note[0] not in 'ABCDEFG' or not note[-1].isdigit(): raise ValueError('invalid bass note')
    t=beat['timbre']
    for n in t['kick_pitch']: number(n,20,400,'kick_pitch')
    number(t['kick_decay'],1,100,'kick_decay');number(t['hat_decay'],1,300,'hat_decay')
    number(t['snare_tone'],0,1,'snare_tone')
    for name,gain in t['gain'].items(): number(gain,0,2,f'gain.{name}')

def resolve(work):
    brief=json.loads((work/'brief.json').read_text())
    kind=brief.get('type')
    if kind not in KINDS: raise ValueError(f'unknown type: {kind}')
    for axis in ('theme','beat','voice'):
        if axis not in brief: raise ValueError(f'missing {axis}')
    theme=preset('themes',brief['theme']); beat=preset('beats',brief['beat']);voice=preset('voices',brief['voice'])
    if 'background' in brief.get('palette',{}): raise ValueError('palette.background removed; use palette.bg')
    theme={**theme,**brief.get('palette',{})}
    validate_theme(theme); validate_beat(beat)
    bpm=90 if brief['beat']=='none' else brief.get('bpm',beat['bpm'])
    if not 40<=bpm<=240: raise ValueError('bpm outside 40..240')
    voice_name=brief.get('voiceName',voice['voiceName'])
    if voice_name not in VOICES: raise ValueError(f'unknown voiceName: {voice_name}')
    lines=brief.get('lines')
    if not isinstance(lines,list) or not 4<=len(lines)<=7 or any(not isinstance(x.get('text'),str) or not x['text'] for x in lines):
        raise ValueError('lines requires 4..7 nonempty text entries')
    if any(not isinstance(line.get('take', 0), int) or isinstance(line.get('take', 0), bool) or line.get('take', 0) < 0 for line in lines):
        raise ValueError('line take must be a nonnegative integer')
    effective={**brief,'palette':theme,'beatDefinition':beat,'bpm':bpm,'voiceName':voice_name,'style':brief.get('style',voice['style']),'model':brief.get('model','gemini-3.8-flash-tts'),'seed':brief.get('seed',7),'lines':[{**line,'style':line.get('style',brief.get('style',voice['style']))} for line in lines]}
    if effective.get('threeD') not in (None,'blender'): raise ValueError('threeD must be blender or omitted')
    (work/'effective.json').write_text(json.dumps(effective,ensure_ascii=False,indent=2)+'\n')
    return effective

if __name__=='__main__': resolve(Path(sys.argv[1]))
