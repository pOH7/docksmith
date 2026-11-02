import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlparse


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
    def test_filtered_tag_lookup_avoids_anonymous_pagination_limit(self):
        cases = [
            (
                "library/nextcloud", "35.0.", "-apache",
                [f"34.0.{i}-apache" for i in range(1100)],
                [f"35.0.{i}-apache" for i in range(110)]
                + ["35.0.999-apache-rc", "135.0.999-apache"],
                "35.0.109-apache",
            ),
            (
                "xream/sub-store", None, "-http-meta",
                [f"2.30.{i}" for i in range(1100)],
                [f"2.31.{i}-http-meta" for i in range(110)]
                + ["2.31.999-http-meta-dev", "2.31.999-http-meta-test"],
                "2.31.109-http-meta",
            ),
        ]

        class PaginationLimitError(Exception):
            pass

        for image, prefix, suffix, old_tags, matching_tags, expected in cases:
            with self.subTest(image=image):
                api = DockerHubAPI()
                tags = old_tags + matching_tags

                def get_page(url, params=None, timeout=None):
                    query = {
                        key: values[0]
                        for key, values in parse_qs(urlparse(url).query).items()
                    }
                    query.update(params or {})
                    page_size = int(query.get("page_size", 10))
                    page = int(query.get("page", 1))
                    offset = (page - 1) * page_size
                    if offset >= 1000:
                        raise PaginationLimitError(
                            "403: pagination offset too large for anonymous requests"
                        )
                    selected = [
                        tag for tag in tags if query.get("name", "") in tag
                    ]
                    next_url = None
                    if offset + page_size < len(selected):
                        query["page"] = page + 1
                        next_url = url.split("?", 1)[0] + "?" + urlencode(query)
                    response = Mock()
                    response.json.return_value = {
                        "results": [
                            {"name": tag}
                            for tag in selected[offset:offset + page_size]
                        ],
                        "next": next_url,
                    }
                    return response

                fake_requests = types.SimpleNamespace(
                    get=Mock(side_effect=get_page),
                    RequestException=PaginationLimitError,
                )
                with patch("dockerhub_api.requests", fake_requests):
                    latest = api.get_latest_tag(image, prefix, suffix)

                self.assertEqual(latest, expected)
                self.assertEqual(fake_requests.get.call_count, 2)

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
