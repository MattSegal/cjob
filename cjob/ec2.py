import os
import sys
import logging
from datetime import datetime
from dateutil import parser
from typing import Optional, List
from time import time

from pydantic import BaseModel

from .config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SECURITY_GROUP = "cjob-security-group"


class EC2InstanceState:
    pending = "pending"
    running = "running"
    stopping = "stopping"
    stopped = "stopped"
    terminated = "terminated"
    shutting_down = "shutting-down"
    rebooting = "rebooting"


class EC2Instance(BaseModel):
    id: str  # AWS Instance ID
    name: Optional[str]  # Instance name, from "Name" tag on instance.
    ip: Optional[str]  # Public IP maybe?
    type: str  # AWS Instance type (eg. "t3.small")
    launched_at: datetime
    state: str

    def is_running(self):
        return self.state == EC2InstanceState.running


def run_job(client, job_id: str, job_func, *args, **kwargs):
    """
    Run a job on a remote server
    """
    create_job(client, job_id)
    logger.info("Waiting 60s for EC2 instance to boot... ")
    time.sleep(60)
    logger.info("Server is hopefully ready.")
    instance = find_instance(job_id)
    output = None
    try:
        logger.info("Attempting to run job %s on instance %s", job_id, instance.id)
        output = job_func(*args, **kwargs)
        logging.info("Job %s succeeded.", job_id)
    except Exception as e:
        # Unknown error.
        logger.exception(f"Job {job_id} failed.")
        raise e
    finally:
        # Always stop the job to prevent dangling jobs.
        stop_job(client, job_id)

    return output


def create_job(client, job_id: str):
    settings = get_settings()
    logger.info(f"Creating EC2 instance {settings.EC2_INSTANCE_TYPE} for job {job_id}... ")

    security_group_id = settings.EC2_SECURITY_GROUP
    if not security_group_id:
        security_group_id = _setup_default_security_group(client)

    ami_id = settings.EC2_AMI
    if not ami_id:
        logger.info("No Amazon Machine Image provided, using latest Ubuntu image.")
        ami_id = get_latest_ubuntu_ami_id(client)
        logger.info(f"Found Ubuntu AMU {ami_id}")

    key_name = _setup_private_key(client)

    kwargs = {
        "MaxCount": 1,
        "MinCount": 1,
        "ImageId": ami_id,
        "InstanceType": settings.EC2_INSTANCE_TYPE,
        "SecurityGroupIds": [security_group_id],
        "KeyName": key_name,
        "InstanceInitiatedShutdownBehavior": settings.EC2_SHUTDOWN_BEHAVIOUR,
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": job_id}],
            }
        ],
    }

    if settings.EC2_IAM_INSTANCE_PROFILE:
        kwargs["IamInstanceProfile"] = ({"Name": settings.EC2_IAM_INSTANCE_PROFILE},)

    if settings.EC2_USE_SPOT:
        logger.info(f"Using a spot EC2 instance. ")
        kwargs["InstanceMarketOptions"] = {
            "MarketType": "spot",
            "SpotOptions": {
                "MaxPrice": settings.EC2_SPOT_MAX_PRICE,
                "SpotInstanceType": "one-time",
            },
        }
    else:
        logger.info(f"Not using a spot EC2 instance.")

    client.run_instances(**kwargs)
    logger.info("Start request sent.")


def start_job(client, job_id: str):
    logger.info(f"Stopping EC2 instances running job {job_id}... ")
    instance_ids = [i.id for i in get_instances(client) if i.name == job_id]
    logger.info(f"Starting EC2 instances {instance_ids}")
    response = client.start_instances(InstanceIds=[instance_ids])
    logger.info(response)


def stop_job(client, job_id: str):
    logger.info(f"Stopping EC2 instances running job {job_id}... ")
    instance_ids = [i.id for i in get_instances(client) if i.name == job_id]
    logger.info(f"Found these EC2 instances to stop: {instance_ids}")
    client.terminate_instances(InstanceIds=instance_ids)
    logger.info("Stop request sent.")


def get_instances(client) -> List[EC2Instance]:
    response = client.describe_instances()
    aws_instances = []
    for reservation in response["Reservations"]:
        for aws_instance in reservation["Instances"]:
            aws_instances.append(aws_instance)

    instances = []
    for aws_instance in aws_instances:
        if aws_instance["State"]["Name"] == EC2InstanceState.terminated:
            continue

        name = ""
        for tag in aws_instance.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]

        if not has_job_prefix(name):
            # Only get cjob created instances
            continue

        # Read IP address
        ip = None
        instance_id = aws_instance["InstanceId"]
        try:
            network_interface = aws_instance["NetworkInterfaces"][0]
            ip = network_interface["Association"]["PublicIp"]
        except (KeyError, IndexError):
            logger.warn("Could not find IP address for instance %s", instance_id)
            pass

        instance = EC2Instance(
            id=instance_id,
            name=name,
            ip=ip,
            type=aws_instance["InstanceType"],
            launched_at=aws_instance["LaunchTime"],
            state=aws_instance["State"]["Name"],
        )
        instances.append(instance)

    return instances


def find_instance(client, name: str) -> EC2Instance:
    instances = get_instances(client)
    for instance in instances:
        if instance.name == name:
            return instance


def cleanup_instances(client):
    """
    Delete old EC2 instances so we don't pay for them
    """
    settings = get_settings()
    instances = get_instances(client)
    stop_instance_ids = []
    for i in instances:
        has_protected_name = any([i.name == i_name for i_name in settings.EC2_PROTECTED_INSTANCES])
        if has_protected_name:
            # Don't kill protected instances
            continue

        uptime_delta = datetime.utcnow() - i.launched_at.replace(tzinfo=None)
        hours = uptime_delta.total_seconds() // 3600
        if hours > settings.EC2_MAX_HOURS:
            launch_time_str = i.launched_at.isoformat()
            logger.info(
                f"Stopping instance {i.name} with id {i.id} with {hours}h uptime since {launch_time_str}"
            )
            stop_instance_ids.append(i.id)

    if stop_instance_ids:
        logger.info("Stopping instance ids %s", stop_instance_ids)
        client.terminate_instances(InstanceIds=stop_instance_ids)
    else:
        logger.info("No instances to stop.")


def cleanup_volumes(client):
    """
    Delete orphaned EC2 volumes so we don't pay for them
    """
    volumes = client.describe_volumes()
    volume_ids = [v["VolumeId"] for v in volumes["Volumes"] if v["State"] == "available"]
    for v_id in volume_ids:
        logger.info(f"Deleting orphaned volume {v_id}")
        client.delete_volume(VolumeId=v_id)

    if not volume_ids:
        logger.info("No volumes to delete.")


def get_latest_ubuntu_ami_id(client) -> str:
    response = client.describe_images(Owners=[UBUNTU_OWNER_ID], Filters=DEFAULT_AMI_FILTERS)
    amis = response["Images"]
    latest = None
    for image in amis:
        if not latest:
            latest = image
            continue

        if parser.parse(image["CreationDate"]) > parser.parse(latest["CreationDate"]):
            latest = image

    return latest["ImageId"]


UBUNTU_OWNER_ID = "099720109477"
DEFAULT_AMI_FILTERS = [
    {"Name": "name", "Values": ["ubuntu/images/*ubuntu-bionic-18.04-amd64-server-*"]},
    {"Name": "owner-id", "Values": [UBUNTU_OWNER_ID]},
    {"Name": "state", "Values": ["available"]},
    {"Name": "root-device-type", "Values": ["ebs"]},
    {"Name": "virtualization-type", "Values": ["hvm"]},
]

JOB_PREFIX = "cjob-"


def add_job_prefix(s: str):
    """Adds "cjob-" to a job id"""
    assert not has_job_prefix(s)
    return JOB_PREFIX + s


def has_job_prefix(s: str):
    return s.startswith(JOB_PREFIX)


def strip_job_prefix(s: str):
    """Removes "cjob-" from a job id"""
    assert has_job_prefix(s)
    return s[len(JOB_PREFIX) :]


def _setup_private_key(client):
    """
    Create a private key at EC2_KEY_FILE_PATH if it does not already exist.
    Does not check the key fingerprint because it's too hard,
    just uses filenames and hope for the best.
    """
    settings = get_settings()
    key_path = settings["EC2_KEY_FILE_PATH"]
    key_name = [p for p in os.path.basename(key_path).split(".")][0]

    response = client.describe_key_pairs()
    keypairs = response["KeyPairs"]
    key_name_already_exists = any([key_name == kp["KeyName"] for kp in keypairs])
    key_path_already_exists = os.path.exists(key_path)

    if key_name_already_exists and key_path_already_exists:
        logger.info("Found private key %s at %s", key_name, key_path)
    elif key_name_already_exists:
        msg = "Found private key named %s in AWS but it does not exist locally, use a different name or move the key file to %s"
        logger.error(msg, key_name, key_path)
        sys.exit(-1)
    elif key_path_already_exists:
        msg = "Found private key named %s in locally but it does not exist in AWS, use a different name or upload the key to AWS."
        logger.error(msg, key_name, key_path)
        sys.exit(-1)
    else:
        logger.info("Creating new private key %s at %s", key_name, key_path)
        response = client.create_key_pair(KeyName=key_name)
        key_contents = response["KeyMaterial"]
        with open(key_path, "w") as f:
            f.write(key_contents)

    return key_name


def _setup_default_security_group(client) -> str:
    """
    Idempotently sets up default security group
    """
    logging.info("No security group specified, trying to find one.")
    # Find VPC
    logging.info("Searching for default VPC...")
    response = client.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    vpc_id = response["Vpcs"][0]["VpcId"]
    logging.info(f"Found default VPC {vpc_id}")
    # Find default security group.
    logging.info("Searching for cjob default security group...")
    response = client.describe_security_groups()
    security_group = None
    for sg in response["SecurityGroups"]:
        if sg["GroupName"] == DEFAULT_SECURITY_GROUP:
            security_group = sg

    if security_group:
        logging.info(f"Found default security group {DEFAULT_SECURITY_GROUP}")
    else:
        logging.info(f"Creating default security group '{DEFAULT_SECURITY_GROUP}'")
        security_group = client.create_security_group(
            Description="Auto-generated security group for cjob tool.",
            GroupName=DEFAULT_SECURITY_GROUP,
            VpcId=vpc_id,
        )

    if not any([p["FromPort"] == 22 for p in security_group["IpPermissions"]]):
        logger.info("Creating ingress rule for port 22 so we can SSH into the server.")
        client.authorize_security_group_ingress(
            GroupName=DEFAULT_SECURITY_GROUP,
            IpPermissions=[
                {
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpProtocol": "tcp",
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH Access"}],
                },
            ],
        )

    if not any([p["IpProtocol"] == "-1" for p in security_group["IpPermissionsEgress"]]):
        logger.info("Creating egress rule for all ports so the server can talk to the internet.")
        client.authorize_security_group_egress(
            GroupName=DEFAULT_SECURITY_GROUP,
            IpPermissions=[
                {
                    "FromPort": "-1",
                    "IpProtocol": "-1",
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "Unlimited Egress"}],
                    "ToPort": "-1",
                },
            ],
        )

    return security_group["GroupId"]
