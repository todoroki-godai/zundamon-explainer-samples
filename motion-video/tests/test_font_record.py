"""Font record must not depend on OS font paths. Run: python3 -m unittest discover -s motion-video/tests -p test_font_record.py -v"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check.py'
spec = importlib.util.spec_from_file_location('motion_video_check_fonts', SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class FontRecordTests(unittest.TestCase):
    def test_missing_file_is_reported_as_unrecorded(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check.font_record(Path(d)), {'status': '未記録', 'families': []})

    def test_empty_or_broken_file_is_reported_as_unrecorded(self):
        with tempfile.TemporaryDirectory() as d:
            for text in ('[]', 'not json', '{}'):
                (Path(d) / 'platform_fonts.json').write_text(text)
                self.assertEqual(check.font_record(Path(d))['status'], '未記録')

    def test_browser_reported_fonts_are_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'platform_fonts.json').write_text(json.dumps(['Noto Sans CJK JP']))
            self.assertEqual(check.font_record(Path(d)), {'status': '記録済み', 'families': ['Noto Sans CJK JP']})

    def test_no_os_font_path_in_source(self):
        self.assertNotIn('/System/Library/Fonts', SCRIPT.read_text())


if __name__ == '__main__':
    unittest.main()
