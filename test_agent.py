import unittest
from unittest.mock import patch

from agent import run_kyc_agent
from sample_data import PRIYA_DISCOVERY_CALL_SAMPLE, seed_clients


class AgentModeTests(unittest.TestCase):
    def test_use_local_demo_environment_flag_skips_sdk_mode(self):
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "test-key", "USE_LOCAL_DEMO": "true"},
            clear=False,
        ):
            result = run_kyc_agent("Client: Alex Morgan", client_id="client_test")

        self.assertEqual(result["mode"], "local_fallback")
        self.assertEqual(result["profile"]["client_id"], "client_test")

    def test_rerunning_anika_profile_does_not_duplicate_semantic_facts(self):
        anika = seed_clients()["client_001"]

        result = run_kyc_agent(
            anika["documents"][0]["text"],
            client_id="client_001",
            existing_profile=anika["profile"],
            force_local=True,
        )

        self.assertEqual(
            result["profile"]["dependents"],
            ["Spouse", "One daughter aged 12"],
        )
        self.assertEqual(
            result["profile"]["goals"],
            [
                "Retirement planning in 18-20 years",
                "Daughter's university education in around 6 years",
                "Maintain liquidity for possible home renovation",
            ],
        )

    def test_rerunning_priya_upgrades_son_with_extracted_age(self):
        result = run_kyc_agent(
            PRIYA_DISCOVERY_CALL_SAMPLE,
            client_id="priya",
            existing_profile={"client_id": "priya", "dependents": ["Son"]},
            force_local=True,
        )

        self.assertEqual(result["profile"]["dependents"], ["Son aged 8"])


if __name__ == "__main__":
    unittest.main()
