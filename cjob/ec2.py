import logging
from datetime import datetime
from dateutil import parser
from typing import Optional, List
from time import time

from pydantic import BaseModel
from botocore.exceptions import ClientError

from .settings import live_settings

# TODO: Util feature to create security group

logger = logging.getLogger(__name__)


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

    def start(self, client):
        logger.info(f"Starting EC2 instance {self.name}")
        response = client.start_instances(InstanceIds=[self.id])
        logger.info(response)

    def stop(self, client):
        logger.info(f"Stopping EC2 instance {self.name}")
        response = client.stop_instances(InstanceIds=[self.id])
        logger.info(response)


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
    logger.info(f"Creating EC2 instance {live_settings.EC2_INSTANCE_TYPE} for job {job_id}... ")

    security_group = live_settings.EC2_SECURITY_GROUP
    if not security_group:
        pass  # Idempotently create a security group

    ami_id = live_settings.EC2_AMI
    if not ami_id:
        pass  # get_latest_ubuntu_ami_id

    kwargs = {
        "MaxCount": 1,
        "MinCount": 1,
        "ImageId": ami_id,
        "InstanceType": live_settings.EC2_INSTANCE_TYPE,
        "SecurityGroupIds": [security_group],
        "KeyName": "autumn",
        "InstanceInitiatedShutdownBehavior": live_settings.SHUTDOWN_BEHAVIOUR,
        "TagSpecifications": [
            {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": job_id}]}
        ],
    }

    if live_settings.EC2_IAM_INSTANCE_PROFILE:
        kwargs["IamInstanceProfile"] = ({"Name": live_settings.EC2_IAM_INSTANCE_PROFILE},)

    if live_settings.EC2_USE_SPOT:
        logger.info(f"Using a spot EC2 instance. ")
        kwargs["InstanceMarketOptions"] = {
            "MarketType": "spot",
            "SpotOptions": {
                "MaxPrice": live_settings.EC2_SPOT_MAX_PRICE,
                "SpotInstanceType": "one-time",
            },
        }
    else:
        logger.info(f"Not using a spot EC2 instance. ")

    client.run_instances(**kwargs)
    logger.info("Create request sent.")


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

        # Read IP address
        ip = None
        try:
            network_interface = aws_instance["NetworkInterfaces"][0]
            ip = network_interface["Association"]["PublicIp"]
        except (KeyError, IndexError):
            pass

        instance = EC2Instance(
            id=aws_instance["InstanceId"],
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
    instances = get_instances(client)
    stop_instance_ids = []
    for i in instances:
        has_protected_name = any(
            [i.name == i_name for i_name in live_settings.EC2_PROTECTED_INSTANCES]
        )
        if has_protected_name:
            # Don't kill protected instances
            continue

        uptime_delta = datetime.utcnow() - i.launched_at.replace(tzinfo=None)
        hours = uptime_delta.total_seconds() // 3600
        if hours > live_settings.EC2_MAX_HOURS:
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
