import importlib.util
import json
import os
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


if __name__ == '__main__':
    unittest.main()
