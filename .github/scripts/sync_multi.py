#!/usr/bin/env python3
"""Multi-component sync orchestrator for complex sync scenarios."""

import sys
import os
import logging
import argparse
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from github_api import GitHubAPI
from dockerhub_api import DockerHubAPI
from docker_operations import DockerOperations
from version_manager import VersionManager
from pr_manager import PRManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_image(docker_ops: DockerOperations, image: str, tag: str,
               target_registry: str, target_namespace: str) -> None:
    """Sync a single image.

    Args:
        docker_ops: Docker operations instance
        image: Source image name
        tag: Image tag
        target_registry: Target registry URL
        target_namespace: Target namespace
    """
    image_name = image.split('/')[-1]
    target_repo = f"{target_registry}/{target_namespace}/{image_name}"
    docker_ops.pull_tag_push(image, tag, target_repo)


def build_and_push_image(docker_ops: DockerOperations, dockerfile: str,
                        image_name: str, tag: str,
                        target_registry: str, target_namespace: str) -> None:
    """Build and push a custom image.

    Args:
        docker_ops: Docker operations instance
        dockerfile: Dockerfile content with {VERSION} placeholder
        image_name: Target image name
        tag: Image tag
        target_registry: Target registry URL
        target_namespace: Target namespace
    """
    logger.info(f"Building custom image: {image_name}")
    dockerfile_content = dockerfile.replace('{VERSION}', tag)
    target_tag = f"{target_registry}/{target_namespace}/{image_name}:{tag}"
    docker_ops.build_image(dockerfile_content, target_tag)
    docker_ops.push_image(f"{target_registry}/{target_namespace}/{image_name}", tag)


def extract_images_from_command(command: str) -> List[str]:
    """Extract image list from a command output.

    Args:
        command: Shell command to execute

    Returns:
        List of image:tag strings
    """
    logger.info(f"Executing command to extract images: {command}")
    try:
        # Execute command and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output to extract images
        # Assumes output contains YAML/JSON with image: lines
        images = []
        for line in result.stdout.split('\n'):
            if 'image:' in line:
                image = line.split('image:')[-1].strip()
                if image:
                    images.append(image)

        return sorted(set(images))
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        raise


def main():
    """Main entry point for multi-component sync."""
    parser = argparse.ArgumentParser(description='Sync multiple components')
    parser.add_argument('--config', required=True, help='JSON config for sync')
    parser.add_argument('--github-token', help='GitHub token')
    parser.add_argument('--docker-registry', help='Docker registry URL')
    parser.add_argument('--docker-username', help='Docker registry username')
    parser.add_argument('--docker-password', help='Docker registry password')
    parser.add_argument('--registry-namespace', help='Registry namespace')
    parser.add_argument('--base-branch', default='master', help='Base branch for PRs')

    args = parser.parse_args()

    # Parse config
    try:
        config = json.loads(args.config)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config JSON: {e}")
        return 1

    # Get configuration from args or environment
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    docker_registry = args.docker_registry or os.getenv('DOCKER_REGISTRY')
    docker_username = args.docker_username or os.getenv('DOCKER_REGISTRY_USER')
    docker_password = args.docker_password or os.getenv('DOCKER_REGISTRY_PASSWORD')
    registry_namespace = args.registry_namespace or os.getenv('DOCKER_REGISTRY_NAMESPACE')
    repo_fullname = os.getenv('GITHUB_REPOSITORY')

    # Validate required parameters
    if not all([github_token, docker_registry, docker_username, docker_password,
                registry_namespace, repo_fullname]):
        logger.error("Missing required configuration")
        return 1

    try:
        # Initialize clients
        gh_api = GitHubAPI(github_token)
        version_mgr = VersionManager()
        docker_ops = DockerOperations(docker_registry, docker_username, docker_password)
        pr_mgr = PRManager(github_token, repo_fullname)

        # Get version tracking key and source repo
        version_key = config.get('version_key')
        source_repo = config.get('source_repo')
        sync_type = config.get('sync_type', 'release')

        # Get latest version
        logger.info(f"Checking for new version from {source_repo}")
        if sync_type == 'release':
            new_version = gh_api.get_latest_release(source_repo)
        elif sync_type == 'tag':
            new_version = gh_api.get_latest_tag(source_repo)
        else:
            raise ValueError(f"Unknown sync type: {sync_type}")

        if new_version is None:
            logger.warning(f"No version found for {source_repo}")
            return 0

        logger.info(f"Latest version: {new_version}")

        # Check if version has changed
        old_version = version_mgr.read_version(version_key)
        logger.info(f"Stored version: {old_version}")

        if old_version == new_version:
            logger.info("No version change detected, skipping sync")
            return 0

        logger.info(f"Version changed from {old_version} to {new_version}")

        # Process each component
        components = config.get('components', [])
        for component in components:
            comp_type = component.get('type')

            if comp_type == 'image':
                # Simple image sync
                images = component.get('images', [])
                for image in images:
                    sync_image(docker_ops, image, new_version,
                             docker_registry, registry_namespace)

            elif comp_type == 'dockerfile':
                # Build from Dockerfile
                dockerfile = component.get('dockerfile')
                image_name = component.get('image_name')
                build_and_push_image(docker_ops, dockerfile, image_name,
                                   new_version, docker_registry, registry_namespace)

            elif comp_type == 'command':
                # Extract images from command
                command = component.get('command').replace('{VERSION}', new_version)
                extracted_images = extract_images_from_command(command)

                for full_image in extracted_images:
                    # Split image:tag
                    if ':' in full_image:
                        image, tag = full_image.rsplit(':', 1)
                    else:
                        image, tag = full_image, new_version

                    sync_image(docker_ops, image, tag,
                             docker_registry, registry_namespace)

        # Update version file
        version_mgr.write_version(version_key, new_version)
        logger.info(f"Updated version file to {new_version}")

        # Create PR
        logger.info("Creating pull request")
        pr_url = pr_mgr.create_and_merge_pr(version_key, new_version, args.base_branch)

        if pr_url:
            logger.info(f"Pull request created: {pr_url}")
            print(f"::notice title=Version Update::Updated {version_key} to {new_version}. PR: {pr_url}")
        else:
            logger.info("No pull request created (no changes)")

        return 0

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        print(f"::error title=Sync Failed::Failed to sync: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
