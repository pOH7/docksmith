import importlib
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = str(REPO_ROOT / ".github/scripts")
sys.path.insert(0, SCRIPTS_DIR)
sys.modules.setdefault("requests", types.ModuleType("requests"))


def load_sync_multi():
    docker_operations = types.ModuleType("docker_operations")
    docker_operations.DockerOperations = object
    sys.modules["docker_operations"] = docker_operations

    pr_manager = types.ModuleType("pr_manager")
    pr_manager.PRManager = object
    sys.modules["pr_manager"] = pr_manager

    return importlib.import_module("sync_multi")


class SyncMultiVersionResolutionTests(unittest.TestCase):
    def test_dockerhub_sync_uses_configured_source_image_and_suffix(self):
        sync_multi = load_sync_multi()
        calls = []

        class FakeGitHubAPI:
            def get_latest_release(self, repo):
                raise AssertionError("GitHub releases should not be used")

            def get_latest_tag(self, repo):
                raise AssertionError("GitHub tags should not be used")

        class FakeDockerHubAPI:
            def get_latest_tag(self, image, tag_prefix=None, tag_suffix=None):
                calls.append((image, tag_prefix, tag_suffix))
                return "2.31.4-http-meta"

        config = {
            "sync_type": "dockerhub",
            "source_image": "xream/sub-store",
            "tag_suffix": "-http-meta",
        }

        version = sync_multi.get_new_version(
            config,
            gh_api=FakeGitHubAPI(),
            dockerhub_api=FakeDockerHubAPI(),
        )

        self.assertEqual(version, "2.31.4-http-meta")
        self.assertEqual(calls, [("xream/sub-store", None, "-http-meta")])


if __name__ == "__main__":
    unittest.main()
