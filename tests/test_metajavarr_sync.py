import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/sync-metajavarr.yml"


class MetaJavarrSyncTests(unittest.TestCase):
    def test_metajavarr_syncs_ghcr_image_to_aliyun(self) -> None:
        self.assertTrue(WORKFLOW.exists())

        content = WORKFLOW.read_text()

        self.assertIn("name: Sync MetaJavarr", content)
        self.assertIn('"version_key": "MetaJavarr/MetaJavarr"', content)
        self.assertIn('"source_repo": "MetaJavarr/MetaJavarr"', content)
        self.assertIn('"sync_type": "tag"', content)
        self.assertIn('"images": ["ghcr.io/metajavarr/metajavarr"]', content)
        self.assertIn("secrets: inherit", content)


if __name__ == "__main__":
    unittest.main()
