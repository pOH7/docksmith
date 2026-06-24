import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github/workflows/sync-anki.yml"


class AnkiSyncTests(unittest.TestCase):
    def test_anki_sync_uses_current_upstream_rust_toolchain(self):
        self.assertTrue(WORKFLOW.exists())

        content = WORKFLOW.read_text()

        self.assertIn("name: Sync Anki", content)
        self.assertIn('"version_key": "ankitects/anki"', content)
        self.assertIn("FROM rust:1.92.0 AS builder", content)


if __name__ == "__main__":
    unittest.main()
