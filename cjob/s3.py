import os
import glob
import logging

from boto3.s3.transfer import TransferConfig

from .settings import live_settings

logger = logging.getLogger(__name__)


# AWS S3 upload settings
S3_UPLOAD_EXTRA_ARGS = {"ACL": "public-read"}
S3_UPLOAD_CONFIG = TransferConfig(
    max_concurrency=2,
)
S3_DOWNLOAD_CONFIG = TransferConfig(
    max_concurrency=2,
    num_download_attempts=3,
)


def list_s3_keys(s3_client, key_prefix: str, key_suffix: str):
    """Returns the item keys in a path in AWS S3"""
    response = s3_client.list_objects_v2(Bucket=live_settings.S3_BUCKET_NAME, Prefix=key_prefix)
    objs = response["Contents"]
    is_truncated = response["IsTruncated"]
    while is_truncated:
        token = response["NextContinuationToken"]
        response = s3_client.list_objects_v2(
            Bucket=live_settings.S3_BUCKET_NAME, Prefix=key_prefix, ContinuationToken=token
        )
        objs += response["Contents"]
        is_truncated = response["IsTruncated"]

    return [o["Key"] for o in objs if o["Key"].endswith(key_suffix)]


def download_s3(s3_client, src_key: str, dest_path: str, quiet: bool, retries: int = 5):
    if quiet:
        logging.disable(logging.INFO)

    retry_count = 0
    while True:
        try:
            _download_s3(s3_client, src_key, dest_path)
            break
        except Exception:
            retry_count += 1
            if retry_count < retries:
                logger.exception(f"Download to {dest_path} failed, trying again.")
            else:
                logger.error(
                    f"Download to {dest_path} failed, tried {retries} times, still failing."
                )
                raise

    if quiet:
        logging.disable(logging.NOTSET)


def _download_s3(s3_client, src_key: str, dest_path: str):
    """Downloads a file from AWS S3"""
    logger.info("Downloading from %s to %s", src_key, dest_path)
    s3_client.download_file(
        live_settings.S3_BUCKET_NAME, src_key, dest_path, Config=S3_DOWNLOAD_CONFIG
    )


def upload_s3(s3_client, src_path: str, dest_key: str):
    """Upload a file or folder to AWS S3"""
    if os.path.isfile(src_path):
        upload_file_s3(s3_client, src_path, dest_key)
    elif os.path.isdir(src_path):
        upload_folder_s3(s3_client, src_path, dest_key)
    else:
        raise ValueError(f"Path is not a file or folder: {src_path}")


def upload_folder_s3(s3_client, folder_path, dest_folder_key):
    """Upload a folder to S3"""
    nodes = glob.glob(os.path.join(folder_path, "**", "*"), recursive=True)
    files = [f for f in nodes if os.path.isfile(f)]
    rel_files = [os.path.relpath(f, folder_path) for f in files]
    for rel_filepath in rel_files:
        src_path = os.path.join(folder_path, rel_filepath)
        dest_key = os.path.join(dest_folder_key, rel_filepath)
        upload_file_s3(s3_client, src_path, dest_key)


def upload_file_s3(s3_client, src_path: str, dest_key: str):
    """Upload a file to S3"""
    logger.info("Uploading from %s to %s", src_path, dest_key)
    s3_client.upload_file(
        src_path,
        live_settings.S3_BUCKET_NAME,
        dest_key,
        ExtraArgs=S3_UPLOAD_EXTRA_ARGS,
        Config=S3_UPLOAD_CONFIG,
    )
