"""Guard against common UTF-8 mojibake in user-facing source files."""

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOJIBAKE_MARKERS = (chr(0x00C3), chr(0x00C2))


class TextEncodingTests(unittest.TestCase):
    def test_user_facing_sources_are_valid_utf8_without_mojibake_markers(self):
        source_files = [
            path for extension in ("*.py", "*.md", "*.css")
            for path in PROJECT_ROOT.rglob(extension)
            if ".venv" not in path.parts and ".git" not in path.parts
        ]
        for source_file in source_files:
            text = source_file.read_text(encoding="utf-8")
            for marker in MOJIBAKE_MARKERS:
                self.assertNotIn(marker, text, source_file)


if __name__ == "__main__":
    unittest.main()
