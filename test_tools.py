import unittest

from sample_data import PRIYA_DISCOVERY_CALL_SAMPLE, PRIYA_FOLLOW_UP_SAMPLE
from tools import (
    calculate_profile_completion,
    local_extract_kyc_profile,
    merge_kyc_profiles,
    normalise_profile_list,
)


class ProfileCompletionTests(unittest.TestCase):
    def test_score_uses_current_form_values(self):
        profile = {
            "name": None,
            "missing_information": [],
            "contradictions": [],
        }

        empty_score = calculate_profile_completion(profile)
        profile["name"] = "Alex Morgan"

        self.assertEqual(calculate_profile_completion(profile), empty_score + 5)

    def test_score_decreases_when_form_value_is_removed(self):
        profile = {
            "income": "INR 20 lakh",
            "missing_information": [],
            "contradictions": [],
        }

        filled_score = calculate_profile_completion(profile)
        profile["income"] = None

        self.assertEqual(calculate_profile_completion(profile), filled_score - 10)


class ProfileListNormalisationTests(unittest.TestCase):
    def test_structured_items_become_editable_json_text(self):
        self.assertEqual(
            normalise_profile_list(
                [{"relationship": "Son", "age": 12}, "Spouse"]
            ),
            ['{"age": 12, "relationship": "Son"}', "Spouse"],
        )

    def test_merge_repairs_structured_items_already_in_profile(self):
        merged = merge_kyc_profiles(
            {"client_id": "client_test", "dependents": [{"name": "Asha"}]},
            {"occupation": "Consultant"},
        )

        self.assertEqual(merged["dependents"], ['{"name": "Asha"}'])

    def test_merge_normalises_structured_agent_list_items(self):
        merged = merge_kyc_profiles(
            {"client_id": "client_test", "dependents": []},
            {"dependents": [{"relationship": "Daughter", "age": 8}]},
        )

        self.assertEqual(
            merged["dependents"],
            ['{"age": 8, "relationship": "Daughter"}'],
        )


class IdentityExtractionTests(unittest.TestCase):
    def test_extracts_name_from_discovery_call_self_introduction(self):
        profile = local_extract_kyc_profile(PRIYA_DISCOVERY_CALL_SAMPLE)

        self.assertEqual(profile["name"], "Priya Kapoor")

    def test_extracts_name_from_follow_up_transcript_title(self):
        profile = local_extract_kyc_profile(PRIYA_FOLLOW_UP_SAMPLE)

        self.assertEqual(profile["name"], "Priya Kapoor")

    def test_extracts_gender_and_pronouns_from_labelled_fields(self):
        profile = local_extract_kyc_profile(
            "Client name: Alex Morgan\nGender: Non-binary\nPronouns: they/them"
        )

        self.assertEqual(profile["gender"], "Non-binary")
        self.assertEqual(profile["pronouns"], "they/them")

    def test_extracts_pronouns_from_sentence(self):
        profile = local_extract_kyc_profile("The client's pronouns are she/her.")

        self.assertEqual(profile["pronouns"], "she/her")


class MaritalStatusExtractionTests(unittest.TestCase):
    def test_infers_married_from_wife_dependent(self):
        profile = local_extract_kyc_profile("Dependents: Wife, one son")

        self.assertEqual(profile["marital_status"], "Married")

    def test_infers_married_from_spouse_dependent(self):
        profile = local_extract_kyc_profile("Spouse and daughter are dependents.")

        self.assertEqual(profile["marital_status"], "Married")

    def test_infers_married_from_husband_dependent(self):
        profile = local_extract_kyc_profile("Her husband and son are dependents.")

        self.assertEqual(profile["marital_status"], "Married")

    def test_explicit_marital_status_takes_precedence(self):
        profile = local_extract_kyc_profile(
            "Marital status: Separated\nDependents: Wife, one son"
        )

        self.assertEqual(profile["marital_status"], "Separated")

    def test_infers_divorced_from_ex_spouse(self):
        profile = local_extract_kyc_profile("His ex-wife is a financial dependent.")

        self.assertEqual(profile["marital_status"], "Divorced")
        self.assertNotIn("Wife", profile["dependents"])

    def test_does_not_extract_ex_husband_as_current_dependent(self):
        profile = local_extract_kyc_profile("Her ex-husband lives elsewhere.")

        self.assertEqual(profile["marital_status"], "Divorced")
        self.assertNotIn("Husband", profile["dependents"])

    def test_does_not_extract_former_spouse_as_current_dependent(self):
        profile = local_extract_kyc_profile("His former spouse lives elsewhere.")

        self.assertEqual(profile["marital_status"], "Divorced")
        self.assertNotIn("Spouse", profile["dependents"])

    def test_infers_widowed_from_late_spouse(self):
        profile = local_extract_kyc_profile("His late wife left him a property.")

        self.assertEqual(profile["marital_status"], "Widowed")

    def test_infers_separated_from_estranged_spouse(self):
        profile = local_extract_kyc_profile("Her estranged husband is a dependent.")

        self.assertEqual(profile["marital_status"], "Separated")

    def test_infers_single_from_unmarried(self):
        profile = local_extract_kyc_profile("The client is unmarried.")

        self.assertEqual(profile["marital_status"], "Single")

    def test_canonicalises_explicit_status_aliases(self):
        cases = {
            "divorcee": "Divorced",
            "widow": "Widowed",
            "unmarried": "Single",
            "living separately": "Separated",
        }

        for source, expected in cases.items():
            with self.subTest(source=source):
                profile = local_extract_kyc_profile(f"Marital status: {source}")
                self.assertEqual(profile["marital_status"], expected)


if __name__ == "__main__":
    unittest.main()
