import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/sync-sub-store.yml"


class SubStoreSyncTests(unittest.TestCase):
    def test_sub_store_uses_dockerhub_tags_as_version_source(self):
        self.assertTrue(WORKFLOW.exists())

        content = WORKFLOW.read_text()

        self.assertIn("name: Sync Sub-Store", content)
        self.assertIn('"version_key": "sub-store-org/Sub-Store"', content)
        self.assertIn('"sync_type": "dockerhub"', content)
        self.assertIn('"source_image": "xream/sub-store"', content)
        self.assertIn('"tag_suffix": "-http-meta"', content)


if __name__ == "__main__":
    unittest.main()
