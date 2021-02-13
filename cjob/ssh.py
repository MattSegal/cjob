import os
import subprocess
import logging

from .ec2 import EC2Instance

logger = logging.getLogger(__name__)

SSH_OPTIONS = {
    "StrictHostKeyChecking": "no",
    # https://superuser.com/questions/522094/how-do-i-resolve-a-ssh-connection-closed-by-remote-host-due-to-inactivity
    "TCPKeepAlive": "yes",
    "ServerAliveInterval": "30",
}


def ssh_interactive(instance: EC2Instance, ssh_key_path: str, **options):
    logger.info(f"Starting SSH session with instance {instance.name}.")
    opts = {**SSH_OPTIONS, **options}
    opt_str = " ".join([f"-o {k}={v}" for k, v in opts.items()])
    cmd_str = f"ssh {opt_str} -i {ssh_key_path} ubuntu@{instance.ip}"
    logger.info("Entering ssh session with: %s", cmd_str)
    subprocess.call(cmd_str, shell=True)
