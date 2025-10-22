"""Version file management for tracking release versions."""

from pathlib import Path
from typing import Optional


class VersionManager:
    """Manages version files in the release-versions directory."""

    def __init__(self, base_dir: str = "release-versions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def get_version_file_path(self, repo: str) -> Path:
        """Get the path to a version file for a given repo.

        Args:
            repo: Repository name (e.g., 'minio/minio' or 'nodejs_14')

        Returns:
            Path to the version file
        """
        # Replace / with _ to create filename
        filename = repo.replace("/", "_") + ".txt"
        return self.base_dir / filename

    def read_version(self, repo: str) -> Optional[str]:
        """Read the stored version for a repository.

        Args:
            repo: Repository name

        Returns:
            Stored version string, or None if file doesn't exist
        """
        version_file = self.get_version_file_path(repo)
        if not version_file.exists():
            return None
        return version_file.read_text().strip()

    def write_version(self, repo: str, version: str) -> None:
        """Write a new version to the version file.

        Args:
            repo: Repository name
            version: Version string to write
        """
        version_file = self.get_version_file_path(repo)
        version_file.write_text(version + "\n")

    def has_version_changed(self, repo: str, new_version: str) -> bool:
        """Check if a new version is different from the stored version.

        Args:
            repo: Repository name
            new_version: New version to compare

        Returns:
            True if version has changed or no previous version exists
        """
        old_version = self.read_version(repo)
        return old_version != new_version
