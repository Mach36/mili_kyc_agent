import unittest
from unittest.mock import patch

from agent import run_kyc_agent


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


if __name__ == "__main__":
    unittest.main()
