import unittest

from streamlit.testing.v1 import AppTest

from sample_data import INCOMPLETE_SAMPLE


class ProfileEditorTests(unittest.TestCase):
    def test_new_client_panel_still_creates_and_selects_client(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        client_name = next(
            widget for widget in app.text_input if widget.label == "Client name"
        )

        client_name.set_value("UI Test Client").run()
        create_button = next(
            widget for widget in app.button if widget.key == "create_client"
        )
        create_button.click().run()

        selected_client_id = app.session_state["selected_client_id"]
        selected_profile = app.session_state["clients"][selected_client_id]["profile"]
        self.assertEqual(selected_profile["name"], "UI Test Client")
        self.assertFalse(app.exception)

    def test_review_action_persists_client_status_and_can_reopen(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        selected_client_id = app.session_state["selected_client_id"]
        original_name = app.session_state["clients"][selected_client_id]["profile"][
            "name"
        ]
        complete_button = next(
            widget
            for widget in app.button
            if widget.key == f"complete_kyc_review_{selected_client_id}"
        )

        complete_button.click().run()

        self.assertTrue(
            app.session_state["clients"][selected_client_id]["kyc_reviewed"]
        )
        self.assertEqual(
            app.session_state["clients"][selected_client_id]["profile"]["name"],
            original_name,
        )
        reopen_button = next(
            widget
            for widget in app.button
            if widget.key == f"reopen_kyc_review_{selected_client_id}"
        )
        reopen_button.click().run()
        self.assertFalse(
            app.session_state["clients"][selected_client_id]["kyc_reviewed"]
        )
        self.assertFalse(app.exception)

    def test_structured_dependent_from_agent_does_not_crash_editor(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        selected_client_id = app.session_state["selected_client_id"]
        clients = app.session_state["clients"]
        profile = clients[selected_client_id]["profile"]
        profile["dependents"] = [
            {"name": "Asha", "relationship": "Daughter", "age": 8}
        ]
        app.session_state["clients"] = clients
        app.session_state["profile_editor_version"] += 1

        app.run()

        dependents = next(
            widget for widget in app.text_area if widget.label == "Dependents"
        )
        self.assertIn('"relationship": "Daughter"', dependents.value)
        self.assertFalse(app.exception)

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
            widget for widget in app.selectbox if widget.label == "Sample data"
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
