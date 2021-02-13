import logging
import pprint
from datetime import datetime
from dateutil.tz import tzutc

import click
import timeago
from tabulate import tabulate

from .ec2 import get_instances, get_latest_ubuntu_ami_id, find_instance
from .settings import live_settings
from .client import get_ec2_client
from .timer import Timer
from .ssh import ssh_interactive

logger = logging.getLogger(__name__)

logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("nose").setLevel(logging.WARNING)

logging.basicConfig(level=logging.INFO)

# TODO: A whole settings thing
# - config file -c flag


@click.group()
def cli():
    """
    CLI tool to run jobs on AWS EC2 instances
    """


@cli.command()
@click.argument("name")
@click.option(
    "--key", type=str, help="Path to AWS private key. Eg. ~/.ssh/wizard.pem", required=True
)
def ssh(name: str):
    """
    SSH into an EC2 instance

    """
    instance = find_instance(name)
    if instance and instance.is_running():
        ssh_interactive(instance)
    elif instance:
        click.echo(f"Instance {name} not running")
    else:
        click.echo(f"Instance {name} not found")


@cli.command()
def settings():
    """
    View current settings values.
    """
    settings_str = pprint.pformat(live_settings.dict(), indent=2)
    print(f"Current cjob settings:\n{settings_str}\n")


@cli.command()
def status():
    """Print the status of all your EC2 instances"""
    client = get_ec2_client(live_settings)
    instances = get_instances(client)
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
    client = get_ec2_client(live_settings)
    with Timer("Fetching Ubuntu AMI data"):
        ami = get_latest_ubuntu_ami_id(client)

    logging.info("Latest Ubuntu AMI is %s", ami)


@click.group()
def cleanup():
    """
    Cleanup dangling AWS bits.
    """


@cleanup.command("instances")
def cleanup_instances():
    """"""

    aws.cleanup_instances()
    aws.cleanup_volumes()


@cleanup.command("volumes")
def cleanup_instances():
    """"""

    aws.cleanup_instances()
    aws.cleanup_volumes()
