import unittest

from tools import local_extract_kyc_profile


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
