"""Run with: python3 -m unittest discover -s motion-video/tests -p test_tts.py -v"""
import importlib.util
import base64
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tts.py"
spec = importlib.util.spec_from_file_location("motion_video_tts", SCRIPT)
tts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts)


class TTSResponseTests(unittest.TestCase):
    def test_extract_audio_from_model_output(self):
        response = {
            "status": "completed",
            "steps": [
                {"type": "model_output", "content": [{"type": "text", "text": "ignored"}]},
                {"type": "model_output", "content": [{"type": "audio", "data": "UklGRg=="}]},
            ],
        }
        self.assertEqual(tts.extract_audio_data(response), "UklGRg==")

    def test_no_audio_reports_status(self):
        with self.assertRaisesRegex(RuntimeError, "status=completed") as caught:
            tts.extract_audio_data({"status": "completed", "steps": []})
        self.assertIn("no audio", str(caught.exception))

    def test_failed_status_reports_error_without_response_dump(self):
        response = {"status": "failed", "error": {"message": "quota exhausted"},
                    "steps": [{"type": "model_output", "content": [{"type": "audio", "data": "ignored"}]}],
                    "secret": "must not appear"}
        with self.assertRaisesRegex(RuntimeError, "status=failed.*quota exhausted") as caught:
            tts.extract_audio_data(response)
        self.assertNotIn("secret", str(caught.exception))


class TTSRequestTests(unittest.TestCase):
    def test_style_is_annotation_and_text_is_verbatim(self):
        body = tts.build_request({"model": "gemini-3.8-flash-tts", "voice": "Puck",
                                  "style": "excited, high energy", "text": "AIで、開発はどこまで変わる？"})
        content = body["input"][0]["content"][0]
        self.assertEqual(content["text"], "AIで、開発はどこまで変わる？")
        self.assertEqual(content["annotations"], [{"type": "speech_metadata", "style": "excited, high energy"}])
        self.assertEqual(body["generation_config"]["speech_config"], [{"voice": "Puck"}])
        self.assertEqual(body["response_format"], {"type": "audio"})

    def test_empty_style_omits_annotations(self):
        content = tts.build_request({"model": "gemini-3.8-flash-tts", "voice": "Kore",
                                     "style": "", "text": "本文だけ。"})["input"][0]["content"][0]
        self.assertNotIn("annotations", content)

    def test_synth_sends_interactions_request_and_uses_new_cache_key(self):
        line = {"text": "本文だけ。", "style": "calm and elegant"}
        brief = {"model": "gemini-3.8-flash-tts", "voiceName": "Puck"}
        wav = b"RIFF" + b"test-wave-data"
        response = {"status": "completed", "steps": [{"type": "model_output", "content": [
            {"type": "audio", "mime_type": "audio/wav", "data": base64.b64encode(wav).decode()}
        ]}]}
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"GOOGLE_GENERATIVE_AI_API_KEY": "test-key", "MOTION_VIDEO_TTS_MOCK": "0"}):
                with mock.patch.object(tts.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as urlopen:
                    path = tts.synth(line, brief, Path(directory))
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "https://generativelanguage.googleapis.com/v1beta/interactions")
            self.assertEqual(json.loads(request.data), tts.build_request({"model":brief["model"],"voice":"Puck",**line}))
            self.assertEqual(path.read_bytes(), wav)
            old_spec = {"model": brief["model"], "voice": brief["voiceName"], **line}
            old_key = hashlib.sha256(json.dumps(old_spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertNotEqual(path.stem, old_key)

    def test_take_changes_only_selected_line_and_preserves_cached_audio(self):
        brief = {"model": "gemini-3.8-flash-tts", "voiceName": "Puck"}
        first = {"text": "一行目。", "style": "bright"}
        second = {"text": "二行目。", "style": "calm"}
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            with mock.patch.dict(os.environ, {"MOTION_VIDEO_TTS_MOCK": "1"}):
                original = tts.synth(first, brief, cache)
                other = tts.synth(second, brief, cache)
                old_bytes = original.read_bytes()
                legacy_spec = {"send_method": tts.SEND_METHOD, "model": brief["model"],
                               "voice": brief["voiceName"], "style": first["style"], "text": first["text"]}
                legacy_key = hashlib.sha256(json.dumps(legacy_spec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self.assertEqual(original.stem, legacy_key)
                updated = tts.synth({**first, "take": 1}, brief, cache)
                self.assertNotEqual(updated, original)
                self.assertNotEqual(updated.read_bytes(), old_bytes)
                self.assertEqual(original.read_bytes(), old_bytes)
                self.assertEqual(tts.synth({**first, "take": 0}, brief, cache), original)
                self.assertEqual(tts.synth(second, brief, cache), other)
                self.assertEqual(len(list(cache.glob('*.wav'))), 3)

    def test_publish_does_not_replace_existing_cache_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice.wav'
            path.write_bytes(b'original')
            tts.publish_audio(path, b'new audio')
            self.assertEqual(path.read_bytes(), b'original')
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_invalid_take_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for take in (-1, 1.5, True, "1"):
                with self.subTest(take=take), self.assertRaisesRegex(ValueError, 'take'):
                    tts.synth({"text": "本文", "style": "", "take": take}, {"voiceName": "Puck"}, Path(directory))


if __name__ == "__main__":
    unittest.main()
