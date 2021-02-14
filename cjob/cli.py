import logging
import pprint
from datetime import datetime
from dateutil.tz import tzutc
import sys

import click
import timeago
from tabulate import tabulate

from . import ec2
from .config import get_settings
from .client import get_ec2_client
from .timer import Timer
from .ssh import ssh_interactive

logger = logging.getLogger(__name__)

logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("nose").setLevel(logging.WARNING)

logging.basicConfig(level=logging.INFO)


@click.group()
def cli():
    """
    CLI tool to run jobs on AWS EC2 instances
    """


@cli.command()
@click.argument("name")
def ssh(name: str):
    """
    SSH into a given EC2 instance.
    """
    settings = get_settings()
    client = get_ec2_client()
    instance = ec2.find_instance(client, name)
    if instance and instance.is_running():
        ssh_interactive(instance, settings.KEY_FILE_PATH)
    elif instance:
        logger.info(f"Instance {name} not running")
    else:
        logger.info(f"Instance {name} not found")


@cli.command()
@click.argument("name")
def start(name: str):
    """
    Start an EC2 instance with a given name.
    """
    if name == "all":
        logger.error("Cannot name a job instance 'all'.")
        sys.exit(-1)

    client = get_ec2_client()
    instance = ec2.find_instance(client, name)
    if instance and instance.is_running():
        logger.info(f"A job instance with name {name} is already running.")
    elif instance:
        logger.info(f"Starting exisitng job instance with {name}: {instance.id}")
        ec2.start_job(client, instance.name)
    else:
        logger.info(f"Creating a new job instance with name {name}")
        job_id = ec2.add_job_prefix(name)
        ec2.create_job(client, job_id)


@cli.command()
@click.argument("name")
def stop(name: str):
    """
    Destroy an EC2 instance with a given name.
    Destroys all cjob instances if name is "all".
    """
    client = get_ec2_client()
    if name == "all":
        for instance in ec2.get_instances(client):
            msg = f"Something has gone wrong. Instance named {instance.name} should not be deleted because it does not have the right prefix in its name."
            assert ec2.has_job_prefix(instance.name), msg
            ec2.stop_job(instance.name)
    else:
        job_id = ec2.add_job_prefix(name)
        ec2.stop_job(client, job_id)


@cli.command()
def settings():
    """
    View current settings values.
    """
    settings_str = pprint.pformat(get_settings().dict(), indent=2)
    print(f"Current cjob settings:\n{settings_str}\n")


@cli.command()
def status():
    """Print the status of all your EC2 instances"""
    client = get_ec2_client()
    instances = ec2.get_instances(client)
    now = datetime.utcnow().replace(tzinfo=tzutc())
    table_data = [
        [
            i.id,
            i.name,
            i.type,
            i.state,
            i.ip,
            timeago.format(i.launched_at, now),
        ]
        for i in instances
    ]
    table_str = tabulate(table_data, headers=["Name", "Type", "Status", "IP", "Launched"])
    print("\n", table_str, "\n")


@cli.command()
def ami():
    """Print the ID of the latest Ubuntu EC2 AMI"""
    client = get_ec2_client()
    with Timer("Fetching Ubuntu AMI data"):
        ami = ec2.get_latest_ubuntu_ami_id(client)

    logging.info("Latest Ubuntu AMI is %s", ami)


@click.group()
def cleanup():
    """
    Cleanup dangling AWS bits.
    """


@cleanup.command("instances")
def cleanup_instances():
    """"""
    pass
    # cleanup_instances()


@cleanup.command("volumes")
def cleanup_volumes():
    """"""
    pass
    # cleanup_volumes()
