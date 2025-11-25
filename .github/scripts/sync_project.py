#!/usr/bin/env python3
"""Main orchestrator script for syncing GitHub releases to homelab."""

import sys
import os
import logging
import argparse
import json
from pathlib import Path
from typing import List

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from github_api import GitHubAPI
from dockerhub_api import DockerHubAPI
from docker_operations import DockerOperations
from minio_operations import MinioOperations
from version_manager import VersionManager
from pr_manager import PRManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_version_transforms(version: str, transform_script: str) -> str:
    """Apply version transformations using Python script.

    Args:
        version: Original version string
        transform_script: Python expression/script to transform version

    Returns:
        Transformed version string, or None if should skip

    Raises:
        ValueError: If script execution fails
    """
    # Default: no transformation
    if not transform_script or transform_script == 'none':
        return version

    try:
        # Create a safe namespace with common modules
        import re
        namespace = {
            'version': version,
            're': re,
        }
        # Execute the transformation script
        exec_statement = f"result = {transform_script}"
        logger.info(f"Executing transform: {repr(exec_statement)}")
        exec(exec_statement, namespace)
        result = namespace['result']

        if result is None:
            logger.info(f"Version {version} skipped by transform script")
        else:
            logger.info(f"Version transformed by script: {version} -> {result}")
        return result
    except Exception as e:
        raise ValueError(f"Failed to execute version transform script: {e}")


def sync_images(
    docker_ops: DockerOperations,
    source_images: List[str],
    version: str,
    docker_registry: str,
    registry_namespace: str,
    dockerfile: str = '',
    target_image: str = ''
) -> None:
    """Unified function to sync Docker images.

    Args:
        docker_ops: Docker operations instance
        source_images: List of source images
        version: Image version/tag
        docker_registry: Docker registry URL
        registry_namespace: Registry namespace
        dockerfile: Optional Dockerfile content with {VERSION} placeholder
        target_image: Optional target image name (without registry prefix)
    """
    # If dockerfile provided, build from Dockerfile
    if dockerfile:
        # Use target_image if provided, otherwise extract from FROM line in Dockerfile
        if not target_image:
            # Extract image name from FROM line (e.g., "FROM lscr.io/linuxserver/jellyfin:{VERSION}")
            import re
            from_match = re.search(r'FROM\s+([^\s:]+)', dockerfile, re.IGNORECASE)
            if from_match:
                from_image = from_match.group(1)
                image_name = from_image.split('/')[-1]
            else:
                raise ValueError("Could not extract image name from Dockerfile FROM line, please provide target_image")
        else:
            image_name = target_image

        logger.info(f"Building custom image from Dockerfile as {image_name}")
        dockerfile_content = dockerfile.replace('{VERSION}', version)
        target_tag = f"{docker_registry}/{registry_namespace}/{image_name}:{version}"
        docker_ops.build_image(dockerfile_content, target_tag)
        docker_ops.push_image(f"{docker_registry}/{registry_namespace}/{image_name}", version)

    # Elif source_images exist, pull and tag to image name extracted from source
    elif source_images:
        logger.info(f"Pulling and tagging {len(source_images)} image(s)")
        for source_image in source_images:
            image_name = source_image.split('/')[-1]
            target_repo = f"{docker_registry}/{registry_namespace}/{image_name}"
            docker_ops.pull_tag_push(source_image, version, target_repo)

    else:
        raise ValueError("Either dockerfile or source_images must be provided")


def main():
    """Main entry point for the sync script."""
    parser = argparse.ArgumentParser(description='Sync GitHub releases to homelab')
    parser.add_argument('--repo', required=True, help='Repository name (e.g., minio/minio)')
    parser.add_argument('--sync-type', required=True, choices=['release', 'tag', 'dockerhub'],
                        help='Type of sync to perform')
    parser.add_argument('--source-images', default='[]',
                        help='JSON array of source images')
    parser.add_argument('--dockerfile', default='',
                        help='Dockerfile content for build_and_push action')
    parser.add_argument('--target-image', help='Target image name (for build_and_push)')
    parser.add_argument('--version-transform', default='"none"',
                        help='JSON string containing Python script to transform version')
    parser.add_argument('--tag-prefix', help='Tag prefix for DockerHub sync (optional)')
    parser.add_argument('--github-token', help='GitHub token (or use GITHUB_TOKEN env var)')
    parser.add_argument('--minio-url', help='MinIO URL (or use MINIO_URL env var)')
    parser.add_argument('--minio-access-key', help='MinIO access key (or use MINIO_ACCESS_KEY env var)')
    parser.add_argument('--minio-secret-key', help='MinIO secret key (or use MINIO_SECRET_KEY env var)')
    parser.add_argument('--docker-registry', help='Docker registry URL (or use DOCKER_REGISTRY env var)')
    parser.add_argument('--docker-username', help='Docker registry username (or use DOCKER_REGISTRY_USER env var)')
    parser.add_argument('--docker-password', help='Docker registry password (or use DOCKER_REGISTRY_PASSWORD env var)')
    parser.add_argument('--registry-namespace', help='Registry namespace for target images (or use DOCKER_REGISTRY_NAMESPACE env var)')
    parser.add_argument('--base-branch', default='master', help='Base branch for PRs')
    parser.add_argument('--repo-fullname', help='Full repository name for PRs (e.g., pOH7/homelab)')

    args = parser.parse_args()

    # Parse JSON arguments
    try:
        source_images = json.loads(args.source_images)
        version_transform_script = json.loads(args.version_transform)
        logger.info(f"Parsed version_transform: {repr(version_transform_script)}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON arguments: {e}")
        logger.error(f"Raw version_transform argument: {repr(args.version_transform)}")
        return 1

    # Get configuration from args or environment
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    minio_url = args.minio_url or os.getenv('MINIO_URL')
    minio_access_key = args.minio_access_key or os.getenv('MINIO_ACCESS_KEY')
    minio_secret_key = args.minio_secret_key or os.getenv('MINIO_SECRET_KEY')
    docker_registry = args.docker_registry or os.getenv('DOCKER_REGISTRY')
    docker_username = args.docker_username or os.getenv('DOCKER_REGISTRY_USER')
    docker_password = args.docker_password or os.getenv('DOCKER_REGISTRY_PASSWORD')
    registry_namespace = args.registry_namespace or os.getenv('DOCKER_REGISTRY_NAMESPACE')
    repo_fullname = args.repo_fullname or os.getenv('GITHUB_REPOSITORY')

    # Validate required parameters
    if not all([github_token, minio_url, minio_access_key, minio_secret_key,
                docker_registry, docker_username, docker_password, registry_namespace, repo_fullname]):
        logger.error("Missing required configuration. Check environment variables or arguments.")
        return 1

    try:
        # Initialize clients
        logger.info(f"Starting sync for {args.repo}")
        gh_api = GitHubAPI(github_token)
        version_mgr = VersionManager()
        docker_ops = DockerOperations(docker_registry, docker_username, docker_password)
        # minio_ops = MinioOperations(minio_url, minio_access_key, minio_secret_key)
        pr_mgr = PRManager(github_token, repo_fullname)

        # Get new version based on sync type
        logger.info(f"Checking for new {args.sync_type} version")
        if args.sync_type == 'release':
            new_version = gh_api.get_latest_release(args.repo)
        elif args.sync_type == 'tag':
            new_version = gh_api.get_latest_tag(args.repo)
        elif args.sync_type == 'dockerhub':
            dockerhub_api = DockerHubAPI()
            new_version = dockerhub_api.get_latest_tag(args.repo, args.tag_prefix)
        else:
            raise ValueError(f"Unknown sync type: {args.sync_type}")

        if new_version is None:
            logger.warning(f"No version found for {args.repo}")
            return 0

        logger.info(f"Latest version: {new_version}")

        # Apply version transformations
        transformed_version = apply_version_transforms(new_version, version_transform_script)
        if transformed_version is None:
            logger.info("Version skipped due to transformation rules")
            return 0

        # Check if version has changed
        old_version = version_mgr.read_version(args.repo)
        logger.info(f"Stored version: {old_version}")

        if old_version == new_version:
            logger.info("No version change detected, skipping sync")
            return 0

        logger.info(f"Version changed from {old_version} to {new_version}")

        # Perform sync operation
        logger.info("Starting sync operation")
        sync_images(
            docker_ops=docker_ops,
            source_images=source_images,
            version=transformed_version,
            docker_registry=docker_registry,
            registry_namespace=registry_namespace,
            dockerfile=args.dockerfile,
            target_image=args.target_image or ''
        )
        logger.info("Sync operation completed successfully")

        # Update version file
        version_mgr.write_version(args.repo, new_version)
        logger.info(f"Updated version file to {new_version}")

        # Create PR with changes
        logger.info("Creating pull request")
        pr_url = pr_mgr.create_and_merge_pr(args.repo, new_version, args.base_branch)

        if pr_url:
            logger.info(f"Pull request created: {pr_url}")
            print(f"::notice title=Version Update::Updated {args.repo} to {new_version}. PR: {pr_url}")
        else:
            logger.info("No pull request created (no changes)")

        return 0

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        print(f"::error title=Sync Failed::Failed to sync {args.repo}: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
