import unittest

from streamlit.testing.v1 import AppTest

from sample_data import INCOMPLETE_SAMPLE


class ProfileEditorTests(unittest.TestCase):
    def test_score_updates_when_a_form_field_changes(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        initial_score = app.session_state["clients"]["client_001"]["profile"][
            "completion_score"
        ]

        name_input = next(widget for widget in app.text_input if widget.label == "Name")
        name_input.set_value("").run()

        updated_score = app.session_state["clients"]["client_001"]["profile"][
            "completion_score"
        ]
        self.assertEqual(updated_score, initial_score - 5)
        self.assertEqual(app.get("progress")[0].value, updated_score)
        self.assertFalse(app.exception)

    def test_progress_bar_turns_green_at_full_completion(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()

        missing_input = next(
            widget for widget in app.text_area if widget.label == "Missing info"
        )
        missing_input.set_value("").run()

        self.assertEqual(app.get("progress")[0].value, 100)
        self.assertTrue(
            any(
                "background-color: #16a34a" in element.value
                for element in app.markdown
            )
        )
        self.assertFalse(app.exception)

    def test_selecting_sample_replaces_upload_and_document_text(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        open_dialog = next(
            widget for widget in app.button if widget.key == "open_add_document"
        )
        open_dialog.click().run()

        sample_input = next(
            widget for widget in app.selectbox if widget.label == "Use sample input"
        )
        sample_input.set_value("Incomplete sample - Kabir").run()

        self.assertEqual(app.session_state["document_upload_version"], 1)

        # AppTest closes dialogs after callbacks, so restore the selected widget
        # state and reopen it to inspect the resulting document text.
        app.session_state["sample_choice_0"] = "Incomplete sample - Kabir"
        open_dialog = next(
            widget for widget in app.button if widget.key == "open_add_document"
        )
        open_dialog.click().run()

        document_text = next(
            widget
            for widget in app.text_area
            if widget.label == "Paste or edit document text"
        )
        self.assertEqual(document_text.value, INCOMPLETE_SAMPLE)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
