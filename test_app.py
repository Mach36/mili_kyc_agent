import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from sample_data import INCOMPLETE_SAMPLE


class ProfileEditorTests(unittest.TestCase):
    def test_app_theme_is_light_only(self):
        app_source = Path("app.py").read_text()
        theme_config = Path(".streamlit/config.toml").read_text()

        self.assertNotIn("light-dark(", app_source)
        self.assertNotIn("color-scheme", app_source)
        self.assertNotIn("CanvasText", app_source)
        self.assertNotIn("color-mix(", app_source)
        self.assertIn('toolbarMode = "minimal"', theme_config)
        self.assertIn('base = "light"', theme_config)

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

    def test_consecutive_empty_creations_only_add_one_unnamed_client(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        initial_client_count = len(app.session_state["clients"])

        create_button = next(
            widget for widget in app.button if widget.key == "create_client"
        )
        create_button.click().run()
        first_unnamed_client_id = app.session_state["selected_client_id"]

        create_button = next(
            widget for widget in app.button if widget.key == "create_client"
        )
        create_button.click().run()

        self.assertEqual(len(app.session_state["clients"]), initial_client_count + 1)
        self.assertEqual(
            app.session_state["selected_client_id"], first_unnamed_client_id
        )
        self.assertIsNone(
            app.session_state["clients"][first_unnamed_client_id]["profile"]["name"]
        )
        self.assertFalse(app.exception)

    def test_entering_details_allows_another_unnamed_client(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        initial_client_count = len(app.session_state["clients"])

        create_button = next(
            widget for widget in app.button if widget.key == "create_client"
        )
        create_button.click().run()
        first_unnamed_client_id = app.session_state["selected_client_id"]

        occupation_input = next(
            widget for widget in app.text_input if widget.label == "Occupation"
        )
        occupation_input.set_value("Consultant").run()

        create_button = next(
            widget for widget in app.button if widget.key == "create_client"
        )
        create_button.click().run()

        self.assertEqual(len(app.session_state["clients"]), initial_client_count + 2)
        self.assertNotEqual(
            app.session_state["selected_client_id"], first_unnamed_client_id
        )
        self.assertEqual(
            app.session_state["clients"][first_unnamed_client_id]["profile"][
                "occupation"
            ],
            "Consultant",
        )
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

    def test_removing_selected_client_selects_another_client(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        removed_client_id = app.session_state["selected_client_id"]

        remove_button = next(
            widget
            for widget in app.button
            if widget.key == "remove_selected_client"
        )
        remove_button.click().run()
        confirm_button = next(
            widget
            for widget in app.button
            if widget.key == f"confirm_remove_client_{removed_client_id}"
        )
        confirm_button.click().run()

        self.assertNotIn(removed_client_id, app.session_state["clients"])
        self.assertIn(
            app.session_state["selected_client_id"],
            app.session_state["clients"],
        )
        self.assertFalse(app.exception)

    def test_removing_final_client_leaves_empty_workspace(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        selected_client_id = app.session_state["selected_client_id"]
        clients = app.session_state["clients"]
        app.session_state["clients"] = {
            selected_client_id: clients[selected_client_id]
        }
        app.run()

        remove_button = next(
            widget
            for widget in app.button
            if widget.key == "remove_selected_client"
        )
        remove_button.click().run()
        confirm_button = next(
            widget
            for widget in app.button
            if widget.key == f"confirm_remove_client_{selected_client_id}"
        )
        confirm_button.click().run()

        self.assertEqual(app.session_state["clients"], {})
        self.assertIsNone(app.session_state["selected_client_id"])
        self.assertTrue(
            any("No clients in the workspace" in info.value for info in app.info)
        )
        self.assertFalse(app.exception)

    def test_structured_dependent_from_agent_renders_as_english(self):
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
        self.assertEqual(dependents.value, "Daughter aged 8")
        self.assertFalse(app.exception)

    def test_malformed_time_horizon_is_repaired_before_rendering(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        selected_client_id = app.session_state["selected_client_id"]
        clients = app.session_state["clients"]
        clients[selected_client_id]["profile"]["time_horizon"] = {
            "Short Term": "12-18 months for home renovation",
            "Long Term": ["Retirement", "Son's education"],
        }
        app.session_state["clients"] = clients
        app.session_state["profile_editor_version"] += 1

        app.run()

        self.assertEqual(
            app.session_state["clients"][selected_client_id]["profile"][
                "time_horizon"
            ],
            {
                "home_renovation": "12-18 months",
                "retirement": "Long term - exact time horizon not confirmed",
                "child_education": "Long term - exact time horizon not confirmed",
            },
        )
        timeline_values = [
            widget.value
            for widget in app.text_input
            if widget.label == "Time horizon"
        ]
        self.assertNotIn('[\'Retirement\', "Son\'s education"]', timeline_values)
        self.assertFalse(app.exception)

    def test_agent_run_emits_profile_tab_redirect(self):
        app = AppTest.from_file("app.py", default_timeout=15).run()
        run_button = next(
            widget for widget in app.button if widget.label == "Run KYC Agent"
        )

        run_button.click().run()

        redirect_frames = [
            frame
            for frame in app.get("iframe")
            if "selectTargetTab" in frame.proto.srcdoc
        ]
        self.assertEqual(len(redirect_frames), 1)
        self.assertIn('targetLabel = "Client profile"', redirect_frames[0].proto.srcdoc)
        self.assertIn("scrollPageToTop", redirect_frames[0].proto.srcdoc)
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
