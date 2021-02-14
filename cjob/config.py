import os
import sys
import logging
from typing import Optional, List

from yaml import safe_load
from pydantic import BaseModel, root_validator

logger = logging.getLogger(__name__)

CONFIG_FILE_NAMES = ["cjob.yml", "cjob.yaml"]


class Settings(BaseModel):

    AWS_REGION: str
    AWS_PROFILE: Optional[str]
    AWS_ACCESS_KEY_ID: Optional[str]
    AWS_SECRET_ACCESS_KEY: Optional[str]

    EC2_INSTANCE_TYPE: str
    EC2_KEY_FILE_PATH: str
    EC2_KEY_NAME: Optional[str]
    EC2_USE_SPOT: bool = False
    EC2_SPOT_MAX_PRICE: Optional[float]
    EC2_IAM_INSTANCE_PROFILE: Optional[str]
    EC2_AMI: Optional[str]
    EC2_SECURITY_GROUP: Optional[str]
    EC2_MAX_HOURS: int = 8
    EC2_PROTECTED_INSTANCES: List[str] = []
    S3_BUCKET_NAME: Optional[str]
    EC2_SHUTDOWN_BEHAVIOUR: str = "terminate"

    @root_validator(pre=True, allow_reuse=True)
    def root_validator(cls, values):
        # Check AWS creds
        access = values.get("AWS_ACCESS_KEY_ID")
        secret = values.get("AWS_SECRET_ACCESS_KEY")
        profile = values.get("AWS_PROFILE")
        msg = "Settings must have both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or AWS_PROFILE."
        assert (access and secret) or profile, msg

        # Check spot price
        is_spot = values.get("EC2_USE_SPOT")
        price = values.get("EC2_SPOT_MAX_PRICE")
        msg = "Must have a EC2_SPOT_MAX_PRICE > 0 if using spot instances."
        assert (not is_spot) or (is_spot and price and price > 0), msg

        return values


_settings = None


def get_settings() -> Settings:
    global _settings
    if not _settings:
        for name in CONFIG_FILE_NAMES:
            if os.path.exists(name):
                with open(name, "r") as f:
                    data = safe_load(f)

                if "AWS_PROFILE" in data:
                    logger.info("Loading AWS creds from AWS_PROFILE: %s", data["AWS_PROFILE"])
                else:
                    logger.info("No AWS profile specified, loading AWS creds from access keys")
                    if not "AWS_ACCESS_KEY_ID" in data:
                        logger.info(
                            "No access key in config, loading from environment variable AWS_ACCESS_KEY_ID"
                        )
                        data["AWS_ACCESS_KEY_ID"] = os.environ.get("AWS_ACCESS_KEY_ID")

                    if not "AWS_SECRET_ACCESS_KEY" in data:
                        logger.info(
                            "No secret access key in config, loading from environment variable AWS_SECRET_ACCESS_KEY"
                        )
                        data["AWS_SECRET_ACCESS_KEY"] = os.environ.get("AWS_SECRET_ACCESS_KEY")

                _settings = Settings(**data)

        if not _settings:
            msg = (
                f"\n\n\tCould not find required config file at {CONFIG_FILE_NAMES}\n\t"
                "See docs at https://github.com/MattSegal/cjob for info on how to configure this tool.\n"
            )
            logger.error(msg)
            sys.exit(-1)

    return _settings
