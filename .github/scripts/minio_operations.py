"""MinIO operations for uploading artifacts."""

from minio import Minio
from minio.error import S3Error
from pathlib import Path
from typing import Optional
import logging
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MinioOperations:
    """Handle MinIO/S3 operations for artifact storage."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = True):
        """Initialize MinIO client.

        Args:
            endpoint: MinIO server endpoint (e.g., 'minio.example.com:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Use HTTPS if True, HTTP if False
        """
        # Remove http:// or https:// prefix if present
        parsed = urlparse(endpoint)
        if parsed.scheme:
            endpoint = parsed.netloc
            secure = parsed.scheme == 'https'

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        logger.info(f"Initialized MinIO client for {endpoint}")

    def file_exists(self, bucket: str, object_name: str) -> bool:
        """Check if a file exists in MinIO.

        Args:
            bucket: Bucket name
            object_name: Object name/path

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(bucket, object_name)
            logger.info(f"File {object_name} exists in bucket {bucket}")
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                logger.info(f"File {object_name} does not exist in bucket {bucket}")
                return False
            logger.error(f"Error checking file existence: {e}")
            raise

    def upload_file(self, bucket: str, source_file: Path, object_name: Optional[str] = None) -> None:
        """Upload a file to MinIO.

        Args:
            bucket: Bucket name
            source_file: Path to local file
            object_name: Destination object name (defaults to filename)

        Raises:
            S3Error: If upload fails
        """
        if object_name is None:
            object_name = source_file.name

        logger.info(f"Uploading {source_file} to {bucket}/{object_name}")

        try:
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket):
                logger.info(f"Creating bucket {bucket}")
                self.client.make_bucket(bucket)

            self.client.fput_object(bucket, object_name, str(source_file))
            logger.info(f"Successfully uploaded {object_name} to {bucket}")

        except S3Error as e:
            logger.error(f"Failed to upload {source_file}: {e}")
            raise

    def download_and_upload(self, url: str, bucket: str, skip_if_exists: bool = True) -> bool:
        """Download a file from URL and upload to MinIO.

        Args:
            url: URL to download from
            bucket: MinIO bucket name
            skip_if_exists: Skip if file already exists in MinIO

        Returns:
            True if file was uploaded, False if skipped

        Raises:
            requests.RequestException: If download fails
            S3Error: If upload fails
        """
        filename = Path(url).name
        logger.info(f"Processing {filename} from {url}")

        # Check if file already exists
        if skip_if_exists and self.file_exists(bucket, filename):
            logger.info(f"File {filename} already exists in {bucket}, skipping")
            return False

        # Download file
        logger.info(f"Downloading {url}")
        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            local_file = Path(filename)
            with open(local_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded {filename}")

            # Upload to MinIO
            self.upload_file(bucket, local_file, filename)

            # Clean up local file
            local_file.unlink()
            logger.info(f"Cleaned up local file {filename}")

            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            raise
        except S3Error as e:
            logger.error(f"Failed to upload {filename}: {e}")
            # Clean up local file if it exists
            if Path(filename).exists():
                Path(filename).unlink()
            raise
