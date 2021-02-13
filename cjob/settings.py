from typing import Optional, List

from pydantic import BaseModel, root_validator


class CloudJobSettings(BaseModel):

    AWS_REGION: str
    EC2_INSTANCE_TYPE: str
    AWS_ACCESS_KEY_ID: Optional[str]
    AWS_SECRET_ACCESS_KEY: Optional[str]
    AWS_PROFILE: Optional[str]
    EC2_USE_SPOT: bool = False
    EC2_SPOT_MAX_PRICE: Optional[float]
    EC2_IAM_INSTANCE_PROFILE: Optional[str]
    EC2_AMI: Optional[str]
    EC2_SECURITY_GROUP: Optional[str]
    EC2_MAX_HOURS: int = 8
    EC2_PROTECTED_INSTANCES: List[str] = []
    S3_BUCKET_NAME: Optional[str]
    SHUTDOWN_BEHAVIOUR: str = "terminate"

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
        msg = "Must have a >0 EC2_SPOT_MAX_PRICE if using spot instances."
        assert (not is_spot) or (is_spot and price and price > 0), msg

        return values


live_settings: Optional[CloudJobSettings] = None


def use_settings(settings: CloudJobSettings):
    global live_settings
    live_settings = settings


test_settings = CloudJobSettings(
    AWS_REGION="ap-southeast-2",
    AWS_PROFILE="default",
    EC2_AMI="ami-080b87fdc6d5ca853",
    EC2_INSTANCE_TYPE="r5.2xlarge",
)

use_settings(test_settings)
