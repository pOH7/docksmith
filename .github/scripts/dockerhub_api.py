"""DockerHub API operations for checking image tags."""

import requests
from typing import Optional, List
import logging
import re

logger = logging.getLogger(__name__)


class DockerHubAPI:
    """Handle DockerHub API operations."""

    def __init__(self):
        self.base_url = "https://registry.hub.docker.com/v2"

    def get_tags(self, image: str, tag_prefix: Optional[str] = None) -> List[str]:
        """Get all tags for a DockerHub image.

        Args:
            image: Image name in format 'owner/image' or 'image' for official images
            tag_prefix: Optional prefix to filter tags (e.g., 'cu124-megapak-')

        Returns:
            List of tag names

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.base_url}/repositories/{image}/tags"
        logger.info(f"Fetching tags for {image}")

        all_tags = []
        try:
            while url:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                tags = [result["name"] for result in data.get("results", [])]
                all_tags.extend(tags)

                # Check for pagination
                url = data.get("next")

            logger.info(f"Found {len(all_tags)} tags for {image}")

            # Filter by prefix if provided
            if tag_prefix:
                filtered_tags = [tag for tag in all_tags if tag.startswith(tag_prefix)]
                logger.info(f"Filtered to {len(filtered_tags)} tags matching prefix '{tag_prefix}'")
                return filtered_tags

            return all_tags

        except requests.RequestException as e:
            logger.error(f"Error fetching tags for {image}: {e}")
            raise

    def get_latest_tag(
        self, image: str, tag_prefix: Optional[str] = None
    ) -> Optional[str]:
        """Get the latest tag for a DockerHub image, sorted by version.

        Args:
            image: Image name in format 'owner/image'
            tag_prefix: Optional prefix to filter tags

        Returns:
            Latest tag name, or None if no tags found

        Raises:
            requests.RequestException: If API request fails
        """
        tags = self.get_tags(image, tag_prefix)

        if not tags:
            logger.warning(f"No tags found for {image}")
            return None

        # Sort tags using version sorting (handles semantic versioning)
        try:
            from packaging import version

            def version_key(tag):
                # Try to parse as version, fallback to string comparison
                try:
                    return version.parse(tag)
                except Exception:
                    return tag

            sorted_tags = sorted(tags, key=version_key, reverse=True)
            latest = sorted_tags[0]
            logger.info(f"Latest tag for {image}: {latest}")
            return latest

        except ImportError:
            # Fallback to simple string sorting if packaging is not available
            logger.warning("'packaging' module not available, using string sorting")
            latest = sorted(tags, reverse=True)[0]
            logger.info(f"Latest tag for {image}: {latest}")
            return latest
