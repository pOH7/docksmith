import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SETUP = REPO_ROOT / ".github/actions/sync-setup/action.yml"


class SyncSetupTests(unittest.TestCase):
    def test_sync_setup_does_not_bootstrap_unused_buildx(self) -> None:
        self.assertTrue(SYNC_SETUP.exists())

        content = SYNC_SETUP.read_text()

        self.assertNotIn("docker/setup-buildx-action", content)
        self.assertIn("docker/login-action", content)


if __name__ == "__main__":
    unittest.main()
