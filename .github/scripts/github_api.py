"""GitHub API operations for checking releases and tags."""

import requests
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class GitHubAPI:
    """Handle GitHub API operations."""

    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub API client.

        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def get_latest_release(self, repo: str) -> Optional[str]:
        """Get the latest release tag for a repository.

        Args:
            repo: Repository in format 'owner/repo'

        Returns:
            Tag name of the latest release, or None if no releases found

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.base_url}/repos/{repo}/releases/latest"
        logger.info(f"Fetching latest release for {repo}")

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            tag_name = response.json().get("tag_name")
            logger.info(f"Latest release for {repo}: {tag_name}")
            return tag_name
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No releases found for {repo}")
                return None
            raise
        except requests.RequestException as e:
            logger.error(f"Error fetching release for {repo}: {e}")
            raise

    def get_latest_tag(self, repo: str) -> Optional[str]:
        """Get the latest tag for a repository.

        Args:
            repo: Repository in format 'owner/repo'

        Returns:
            Name of the latest tag, or None if no tags found

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.base_url}/repos/{repo}/tags"
        logger.info(f"Fetching latest tag for {repo}")

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            tags = response.json()
            if tags:
                tag_name = tags[0].get("name")
                logger.info(f"Latest tag for {repo}: {tag_name}")
                return tag_name
            logger.warning(f"No tags found for {repo}")
            return None
        except requests.RequestException as e:
            logger.error(f"Error fetching tags for {repo}: {e}")
            raise

    def get_all_tags(self, repo: str) -> List[str]:
        """Get all tags for a repository.

        Args:
            repo: Repository in format 'owner/repo'

        Returns:
            List of tag names

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.base_url}/repos/{repo}/tags"
        logger.info(f"Fetching all tags for {repo}")

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            tags = response.json()
            tag_names = [tag.get("name") for tag in tags]
            logger.info(f"Found {len(tag_names)} tags for {repo}")
            return tag_names
        except requests.RequestException as e:
            logger.error(f"Error fetching tags for {repo}: {e}")
            raise
