import os
import boto3


def settings_factory(**kwargs):
    def get_settings():
        return {
            "AWS_REGION": "ap-southeast-2",
            "AWS_PROFILE": "default",
            "EC2_INSTANCE_TYPE": "r5.2xlarge",
            "EC2_KEY_FILE_PATH": "~/.ssh/testkey.pem",
            **kwargs,
        }

    return get_settings


def create_test_instance(client, name, **kwargs):
    run_kwargs = {
        "MaxCount": 1,
        "MinCount": 1,
        "ImageId": "ami-076a5bf4a712000ed",
        "InstanceType": "r5.2xlarge",
        "SecurityGroupIds": [],
        "KeyName": "zzz",
        "InstanceInitiatedShutdownBehavior": "terminate",
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": name}],
            }
        ],
        **kwargs,
    }
    resp = client.run_instances(**run_kwargs)
    return resp["Instances"][0]["InstanceId"]