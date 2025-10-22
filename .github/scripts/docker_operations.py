"""Docker operations for building, pulling, and pushing images."""

import docker
from docker.errors import DockerException, BuildError, APIError
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class DockerOperations:
    """Handle Docker operations for image management."""

    def __init__(self, registry: str, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize Docker client and login to registry if credentials provided.

        Args:
            registry: Docker registry URL (e.g., 'registry.cn-hangzhou.aliyuncs.com')
            username: Registry username
            password: Registry password
        """
        try:
            self.client = docker.from_env()
            self.registry = registry

            if username and password:
                logger.info(f"Logging into registry: {registry}")
                self.client.login(username=username, password=password, registry=registry)
                logger.info("Successfully logged into registry")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def pull_image(self, image: str, tag: str) -> str:
        """Pull a Docker image from a registry.

        Args:
            image: Image name (e.g., 'minio/minio')
            tag: Image tag

        Returns:
            Full image name with tag

        Raises:
            DockerException: If pull operation fails
        """
        full_image = f"{image}:{tag}"
        logger.info(f"Pulling image: {full_image}")

        try:
            self.client.images.pull(image, tag=tag)
            logger.info(f"Successfully pulled {full_image}")
            return full_image
        except APIError as e:
            logger.error(f"Failed to pull {full_image}: {e}")
            raise

    def tag_image(self, source_image: str, target_repo: str, tag: str) -> str:
        """Tag an image with a new repository and tag.

        Args:
            source_image: Source image name with tag (e.g., 'minio/minio:v1.0')
            target_repo: Target repository (e.g., 'registry.cn-hangzhou.aliyuncs.com/pohvii/minio')
            tag: New tag

        Returns:
            Full target image name

        Raises:
            DockerException: If tag operation fails
        """
        target_image = f"{target_repo}:{tag}"
        logger.info(f"Tagging {source_image} as {target_image}")

        try:
            image = self.client.images.get(source_image)
            image.tag(target_repo, tag=tag)
            logger.info(f"Successfully tagged as {target_image}")
            return target_image
        except DockerException as e:
            logger.error(f"Failed to tag image: {e}")
            raise

    def push_image(self, repository: str, tag: str) -> None:
        """Push an image to the registry.

        Args:
            repository: Repository name (e.g., 'registry.cn-hangzhou.aliyuncs.com/pohvii/minio')
            tag: Image tag

        Raises:
            DockerException: If push operation fails
        """
        logger.info(f"Pushing {repository}:{tag}")

        try:
            for line in self.client.images.push(repository, tag=tag, stream=True, decode=True):
                if 'error' in line:
                    raise DockerException(f"Push failed: {line['error']}")
                if 'status' in line:
                    logger.debug(f"Push status: {line['status']}")

            logger.info(f"Successfully pushed {repository}:{tag}")
        except (APIError, DockerException) as e:
            logger.error(f"Failed to push {repository}:{tag}: {e}")
            raise

    def build_image(self, dockerfile: str, tag: str, buildargs: Optional[Dict[str, str]] = None) -> None:
        """Build a Docker image from a Dockerfile string.

        Args:
            dockerfile: Dockerfile content as a string
            tag: Tag for the built image
            buildargs: Optional build arguments

        Raises:
            BuildError: If build fails
        """
        logger.info(f"Building image: {tag}")

        try:
            # Create a file-like object from the Dockerfile string
            import io
            dockerfile_obj = io.BytesIO(dockerfile.encode('utf-8'))

            image, build_logs = self.client.images.build(
                fileobj=dockerfile_obj,
                tag=tag,
                rm=True,
                buildargs=buildargs or {}
            )

            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())

            logger.info(f"Successfully built {tag}")

        except BuildError as e:
            logger.error(f"Failed to build {tag}: {e}")
            raise
        except APIError as e:
            logger.error(f"Docker API error while building {tag}: {e}")
            raise

    def pull_tag_push(self, source_image: str, source_tag: str, target_repo: str) -> None:
        """Pull an image, re-tag it, and push to target registry.

        Args:
            source_image: Source image name (e.g., 'minio/minio')
            source_tag: Source tag
            target_repo: Target repository (e.g., 'registry.cn-hangzhou.aliyuncs.com/pohvii/minio')

        Raises:
            DockerException: If any operation fails
        """
        # Pull
        full_source = self.pull_image(source_image, source_tag)

        # Tag
        self.tag_image(full_source, target_repo, source_tag)

        # Push
        self.push_image(target_repo, source_tag)
