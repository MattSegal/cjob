"""
Tests for EC2 instance lookup.
"""
import boto3
from moto import mock_ec2

import cjob.ec2 as ec2
from tests.utils import create_test_instance


@mock_ec2
def test_get_instances__with_no_instances():
    client = boto3.client("ec2", region_name="ap-southeast-2")
    instances = ec2.get_instances(client)
    assert instances == []


@mock_ec2
def test_get_instances__with_no_cjob_instances():
    client = boto3.client("ec2", region_name="ap-southeast-2")
    create_test_instance(client, "foo")
    create_test_instance(client, "when-harry-met-sally")
    create_test_instance(client, "")
    instances = ec2.get_instances(client)
    assert instances == []


@mock_ec2
def test_get_instances__with_mixed_instances():
    client = boto3.client("ec2", region_name="ap-southeast-2")
    id_a = create_test_instance(client, ec2.add_job_prefix("foo"))
    id_b = create_test_instance(client, ec2.add_job_prefix("bar-baz"))
    create_test_instance(client, "foo")
    create_test_instance(client, "when-harry-met-sally")
    create_test_instance(client, "")
    instances = ec2.get_instances(client)
    # Only prefixed instances count
    assert len(instances) == 2
    assert instances[0].id == id_a
    assert instances[0].name == ec2.add_job_prefix("foo")
    assert instances[0].state == "running"

    assert instances[1].id == id_b
    assert instances[1].name == ec2.add_job_prefix("bar-baz")
    assert instances[1].state == "running"

    # Terminated instances don't count
    client.terminate_instances(InstanceIds=[id_a])
    instances = ec2.get_instances(client)
    assert len(instances) == 1
    assert instances[0].id == id_b
    assert instances[0].name == ec2.add_job_prefix("bar-baz")
    assert instances[0].state == "running"


@mock_ec2
def test_find_instance__with_no_instances():
    client = boto3.client("ec2", region_name="ap-southeast-2")
    name = ec2.add_job_prefix("foo")
    instance = ec2.find_instance(client, name)
    assert instance is None


@mock_ec2
def test_find_instance__with_mixed_instances__when_not_exists():
    client = boto3.client("ec2", region_name="ap-southeast-2")
    create_test_instance(client, "foo")
    create_test_instance(client, "when-harry-met-sally")
    create_test_instance(client, "")
    create_test_instance(client, ec2.add_job_prefix("bar-baz"))
    name = ec2.add_job_prefix("foo")
    instance = ec2.find_instance(client, name)
    assert instance is None


@mock_ec2
def test_find_instance__with_mixed_instances__when_exists():
    client = boto3.client("ec2", region_name="ap-southeast-2")
    name = ec2.add_job_prefix("foo")
    create_test_instance(client, "foo")
    create_test_instance(client, "when-harry-met-sally")
    create_test_instance(client, "")
    create_test_instance(client, ec2.add_job_prefix("bar-baz"))
    instance_id = create_test_instance(client, name)
    instance = ec2.find_instance(client, name)
    assert instance is not None
    assert instance.id == instance_id
    assert instance.name == name
    assert instance.state == "running"
