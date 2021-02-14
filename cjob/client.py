import boto3

from .config import get_settings, Settings


def get_ec2_client():
    settings = get_settings()
    session = _get_session(settings)
    return session.client("ec2")


def get_s3_client():
    settings = get_settings()
    session = _get_session(settings)
    return session.client("s3")


def _get_session(settings: Settings):
    if settings.AWS_PROFILE:
        return boto3.session.Session(
            region_name=settings.AWS_REGION, profile_name=settings.AWS_PROFILE
        )
    else:
        return boto3.session.Session(
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
