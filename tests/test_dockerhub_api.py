import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / ".github/scripts"))
sys.modules.setdefault("requests", types.ModuleType("requests"))

from dockerhub_api import DockerHubAPI


class StubDockerHubAPI(DockerHubAPI):
    def __init__(self, tags):
        self.tags = tags
        self.calls = []

    def get_tags(self, image, tag_prefix=None, tag_suffix=None):
        self.calls.append((image, tag_prefix, tag_suffix))
        tags = self.tags
        if tag_prefix:
            tags = [tag for tag in tags if tag.startswith(tag_prefix)]
        if tag_suffix:
            tags = [tag for tag in tags if tag.endswith(tag_suffix)]
        return tags


class DockerHubAPITests(unittest.TestCase):
    def test_latest_tag_filters_suffix_and_sorts_by_embedded_version(self):
        api = StubDockerHubAPI([
            "2.9.0-http-meta",
            "2.31.3-http-meta",
            "2.31.10-http-meta",
            "2.31.4",
            "latest",
        ])

        latest = api.get_latest_tag("xream/sub-store", tag_suffix="-http-meta")

        self.assertEqual(latest, "2.31.10-http-meta")
        self.assertEqual(api.calls, [("xream/sub-store", None, "-http-meta")])


if __name__ == "__main__":
    unittest.main()
