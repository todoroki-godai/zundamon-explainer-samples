import json
import math
import sys
import wave
from pathlib import Path

FPS = 30

def run(work):
    brief = json.loads((work / 'effective.json').read_text())
    paths = json.loads((work / 'tts_paths.json').read_text())
    bpm = brief['bpm']
    beat = 60 * FPS / bpm
    cursor = 0
    lines = []
    for path in paths:
        with wave.open(path) as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (24000, 1, 2):
                raise ValueError('TTS audio must be 24 kHz mono s16 WAV')
            duration = math.ceil(wav.getnframes() / 24000 * FPS)
        start = math.ceil(cursor / beat) * beat
        start = math.ceil(start)
        lines.append({'start': start, 'frames': duration, 'wav': path})
        cursor = start + duration + math.ceil(beat)
    intro = 90 if brief.get('threeD') == 'blender' else 0
    main = math.ceil(cursor / beat) * beat
    total = intro + math.ceil(main)
    if not 15 * FPS <= total <= 45 * FPS:
        raise ValueError(f'video duration {total/FPS:.2f}s outside 15-45s')
    result = {'fps':FPS,'bpm':bpm,'intro_frames':intro,'main_frames':math.ceil(main),'total_frames':total,'lines':lines}
    (work/'timeline.json').write_text(json.dumps(result, indent=2))
    return result

if __name__ == '__main__':
    run(Path(sys.argv[1]))
