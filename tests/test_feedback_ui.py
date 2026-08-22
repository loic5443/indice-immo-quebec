"""Focused presentation checks for the private beta feedback journey."""

import unittest

from streamlit.testing.v1 import AppTest


class FeedbackUiTests(unittest.TestCase):
    def test_guest_gets_a_clear_account_path(self):
        app = AppTest.from_string(
            "import components.feedback as page\n"
            "original_is_authenticated = page.is_authenticated\n"
            "try:\n"
            "    page.is_authenticated = lambda: False\n"
            "    page.show_feedback()\n"
            "finally:\n"
            "    page.is_authenticated = original_is_authenticated\n"
        ).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertIn("Accéder à Mon compte", [button.label for button in app.button])

    def test_authenticated_user_sees_privacy_guidance_and_only_own_history(self):
        app = AppTest.from_string(
            "import components.feedback as page\n"
            "original_is_authenticated = page.is_authenticated\n"
            "original_current_user = page.current_user\n"
            "original_list_feedback = page.list_feedback\n"
            "try:\n"
            "    page.is_authenticated = lambda: True\n"
            "    page.current_user = lambda: {'id': 7}\n"
            "    page.list_feedback = lambda user_id, database: [{'id': 1, 'category': 'Suggestion', 'status': 'new'}] if user_id == 7 else []\n"
            "    page.show_feedback()\n"
            "finally:\n"
            "    page.is_authenticated = original_is_authenticated\n"
            "    page.current_user = original_current_user\n"
            "    page.list_feedback = original_list_feedback\n"
        ).run(timeout=20)
        text = " ".join(item.value for item in app.markdown) + " ".join(item.value for item in app.caption)
        self.assertIn("N’indiquez pas de mot de passe", text)
        self.assertIn("uniquement vos propres retours", text)
        self.assertEqual(app.selectbox[0].label, "Où étiez-vous?")
        self.assertIn("Envoyer mon retour", [button.label for button in app.button])


if __name__ == "__main__":
    unittest.main()
