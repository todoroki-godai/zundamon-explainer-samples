"""Browser-free tests for the voice interval silence boundary."""
import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check.py'
spec = importlib.util.spec_from_file_location('motion_video_check', SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class SilenceBoundaryTests(unittest.TestCase):
    def test_natural_pause_passes_and_long_pause_fails(self):
        rate = 24000
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice.wav'
            for gap, expected in ((0.8, False), (1.2, True)):
                with self.subTest(gap=gap):
                    tone = (np.sin(2 * np.pi * 440 * np.arange(rate) / rate) * 12000).astype('<i2')
                    samples = np.concatenate((tone, np.zeros(round(gap * rate), dtype='<i2'), tone))
                    with wave.open(str(path), 'wb') as wav:
                        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate)
                        wav.writeframes(samples.tobytes())
                    self.assertEqual(check.detect_silence(path, 0, len(samples) / rate), expected)


if __name__ == '__main__':
    unittest.main()
