import unittest

from scripts.configure_brevo_key import valid_key


class BrevoKeyValidationTests(unittest.TestCase):
    def test_rejects_empty_and_short_values(self):
        self.assertFalse(valid_key(""))
        self.assertFalse(valid_key("short"))

    def test_accepts_a_complete_trimmed_value(self):
        self.assertTrue(valid_key("x" * 20))

    def test_rejects_spaces_added_by_accident(self):
        self.assertFalse(valid_key(" " + ("x" * 20)))
        self.assertFalse(valid_key(("x" * 20) + " "))
