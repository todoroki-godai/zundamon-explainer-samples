"""Auxiliary checks for known direct CSS text-color forms; browser coverage is authoritative."""
import json
import re
from pathlib import Path
from resolve import validate_theme

ROOT=Path(__file__).resolve().parents[1]
THEMES=('neon','wa','pop','cinema','minimal','retro')

def check_scene(work):
    html=(work/'scene.html').read_text()
    if not re.search(r'__render|scene\.js',html): raise ValueError('missing renderer reference')
    # This only catches known syntax and is intentionally not the readability gate.
    if re.search(r'(?<![\w-])(?:color|-webkit-text-fill-color)\s*:\s*(?:#[0-9a-fA-F]{3,8}\b|rgba?\s*\()',html):
        raise ValueError('known direct text color')
    if re.search(r'\b(?:clip-path|mask-image)\s*:',html):raise ValueError('known clip-path')
    return True

def check_themes(root=ROOT/'presets/themes'):
    for name in THEMES:validate_theme(json.loads((root/f'{name}.json').read_text()))

if __name__=='__main__':
    import sys
    check_scene(Path(sys.argv[1]));check_themes();print('PASS auxiliary known syntax and 6 themes')
