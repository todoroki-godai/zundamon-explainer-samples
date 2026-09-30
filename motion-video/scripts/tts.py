import base64
import binascii
import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path

SEND_METHOD = "interactions-v1"


def build_request(spec):
    content = {"type": "text", "text": spec["text"]}
    if spec["style"]:
        content["annotations"] = [{"type": "speech_metadata", "style": spec["style"]}]
    return {
        "model": spec["model"],
        "input": [{"type": "user_input", "content": [content]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": spec["voice"]}]},
    }


def extract_audio_data(result):
    status = result.get("status", "unknown")
    error = result.get("error")
    message = error.get("message") if isinstance(error, dict) else error
    if status == "completed":
        for step in result.get("steps", []):
            for content in step.get("content", []):
                if content.get("type") == "audio" and content.get("data"):
                    return content["data"]
    raise RuntimeError(f"TTS response has no audio: status={status}, error={message or 'none'}")


def publish_audio(path, raw, pcm=False):
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix='.wav')
    os.close(fd)
    try:
        if pcm:
            with wave.open(temporary, 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(raw)
        else:
            Path(temporary).write_bytes(raw)
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        os.unlink(temporary)


def synth(line, brief, cache):
    spec = {"send_method": SEND_METHOD, "model": brief.get("model", "gemini-3.8-flash-tts"), "voice": brief["voiceName"], "style": line["style"], "text": line["text"]}
    take = line.get('take', 0)
    if not isinstance(take, int) or isinstance(take, bool) or take < 0:
        raise ValueError('line take must be a nonnegative integer')
    if take:
        spec['take'] = take
    key = hashlib.sha256(json.dumps(spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    path = cache / (key + ".wav")
    if path.exists():
        return path
    cache.mkdir(parents=True, exist_ok=True)
    if os.environ.get("MOTION_VIDEO_TTS_MOCK") == "1":
        import numpy as np

        seconds = max(2.2, len(line["text"]) * 0.115 + 0.8)
        t = np.arange(round(seconds * 24000)) / 24000
        envelope = np.minimum(1, t * 8) * np.minimum(1, (seconds-t) * 8)
        freq = 180 + int(key[:3], 16) % 150
        pcm = (np.sin(2*np.pi*(freq*t + 40*t*t)) * envelope * 12000).astype('<i2').tobytes()
        publish_audio(path, pcm, pcm=True)
        return path
    api_key = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_GENERATIVE_AI_API_KEY is not set")
    body = build_request(spec)
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read()).get("error", {}).get("message", "request failed").replace(api_key, "[redacted]")
        except Exception:
            message = "request failed"
        raise RuntimeError(f"TTS HTTP {exc.code}: {message}") from None
    except urllib.error.URLError:
        raise RuntimeError("TTS request failed") from None
    try:
        raw = base64.b64decode(extract_audio_data(result), validate=True)
    except (binascii.Error, ValueError):
        raise RuntimeError("TTS response has invalid audio data") from None
    publish_audio(path, raw, pcm=raw[:4] != b'RIFF')
    return path


def run(work):
    brief = json.loads((work / 'effective.json').read_text())
    paths = [synth(line, brief, work / ('tts_cache_mock' if os.environ.get('MOTION_VIDEO_TTS_MOCK') == '1' else 'tts_cache')) for line in brief['lines']]
    (work / 'tts_paths.json').write_text(json.dumps([str(p) for p in paths]))


if __name__ == '__main__':
    run(Path(sys.argv[1]))
