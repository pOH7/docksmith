import importlib.util
import json
import os
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    'sync_pinned_images',
    Path(__file__).parents[1] / '.github/scripts/sync_pinned_images.py',
)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class PinnedImageValidationTests(unittest.TestCase):
    def assert_rejected_before_docker(self, images):
        with patch.dict(os.environ, {'MIRROR_IMAGES': json.dumps(images)}):
            with patch.object(sync.subprocess, 'run') as docker:
                with self.assertRaises(ValueError):
                    sync.main()
                docker.assert_not_called()

    def test_mutable_source_is_rejected(self):
        self.assert_rejected_before_docker([
            {'source': 'nextcloud:latest', 'name': 'nextcloud', 'tag': '35.0.2-apache'},
        ])

    def test_invalid_later_item_prevents_partial_publish(self):
        self.assert_rejected_before_docker([
            {'source': 'nextcloud:35.0.2-apache@sha256:' + 'a' * 64,
             'name': 'nextcloud', 'tag': '35.0.2-apache'},
            {'source': 'mysql:8.4@sha256:' + 'b' * 64,
             'name': '../mysql', 'tag': '8.4'},
        ])

    def test_transient_registry_failure_is_retried(self):
        failure = subprocess.CalledProcessError(1, ['docker', 'pull'])
        with patch.object(sync.subprocess, 'run', side_effect=[failure, None]) as docker:
            with patch.object(sync.time, 'sleep') as wait:
                sync.transfer(['pull', 'example@sha256:' + 'a' * 64], timeout=600)
        self.assertEqual(docker.call_count, 2)
        wait.assert_called_once_with(5)

    def test_registry_retry_budget_is_bounded(self):
        failure = subprocess.CalledProcessError(1, ['docker', 'pull'])
        with patch.object(sync.subprocess, 'run', side_effect=failure) as docker:
            with patch.object(sync.time, 'sleep'):
                with self.assertRaises(subprocess.CalledProcessError):
                    sync.transfer(['pull', 'example@sha256:' + 'a' * 64], timeout=600)
        self.assertEqual(docker.call_count, 5)


if __name__ == '__main__':
    unittest.main()
