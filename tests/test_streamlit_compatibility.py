"""Guard against Streamlit APIs scheduled for removal."""

import unittest
from pathlib import Path


class StreamlitCompatibilityTests(unittest.TestCase):
    def test_components_do_not_use_the_removed_container_width_parameter(self):
        components = Path(__file__).resolve().parents[1] / "components"
        offenders = [
            source.relative_to(components).as_posix()
            for source in components.rglob("*.py")
            if "use_container_width" in source.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
