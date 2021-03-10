"""
Tests for private key creation.
"""
import os

import boto3
import pytest
from moto import mock_ec2

import cjob.ec2 as ec2
from tests.utils import settings_factory


@mock_ec2
def test_create_key__with_no_existing_key(monkeypatch, tmpdir):
    """
    Ensure a key is created when it does not exist locally or in AWS.
    """
    # Create a place to put the EC2 key pair
    keypath = os.path.join(tmpdir, "testkey.pem")
    get_test_settings = settings_factory(EC2_KEY_FILE_PATH=keypath)
    monkeypatch.setattr(ec2, "get_settings", get_test_settings)

    assert not os.path.exists(keypath)

    client = boto3.client("ec2", region_name="ap-southeast-2")
    client.create_key_pair(KeyName="otherkey")
    key_name = ec2._setup_private_key(client)
    assert os.path.exists(keypath)
    assert key_name == "testkey"
    with open(keypath, "r") as f:
        key_contents = f.readlines()

    assert len(key_contents) == 27
    assert key_contents[0] == "-----BEGIN RSA PRIVATE KEY-----\n"
    assert key_contents[-1] == "-----END RSA PRIVATE KEY-----\n"


@mock_ec2
def test_create_key__with_existing_key_locally_and_aws(monkeypatch, tmpdir):
    """
    Don't do anything if they key already exists locally and in AWS.
    Don't check the fingerprint.
    """
    # Create a place to put the EC2 key pair
    keypath = os.path.join(tmpdir, "testkey.pem")
    get_test_settings = settings_factory(EC2_KEY_FILE_PATH=keypath)
    monkeypatch.setattr(ec2, "get_settings", get_test_settings)

    with open(keypath, "w") as f:
        f.write(_PRIVATE_KEY)

    client = boto3.client("ec2", region_name="ap-southeast-2")
    client.create_key_pair(KeyName="testkey")
    key_name = ec2._setup_private_key(client)
    assert key_name == "testkey"


@mock_ec2
def test_create_key__with_existing_key_locally_but_not_aws(monkeypatch, tmpdir):
    """
    Ensure an error happens when the key is present locally but not in AWS.
    """
    # Create a place to put the EC2 key pair
    keypath = os.path.join(tmpdir, "testkey.pem")
    get_test_settings = settings_factory(EC2_KEY_FILE_PATH=keypath)
    monkeypatch.setattr(ec2, "get_settings", get_test_settings)

    with open(keypath, "w") as f:
        f.write(_PRIVATE_KEY)

    client = boto3.client("ec2", region_name="ap-southeast-2")
    client.create_key_pair(KeyName="otherkey")

    with pytest.raises(SystemExit):
        ec2._setup_private_key(client)


@mock_ec2
def test_create_key__with_existing_key_aws_but_not_locally(monkeypatch, tmpdir):
    """
    Ensure an error happens when the key is present in AWS but not in locally.
    """
    # Create a place to put the EC2 key pair
    keypath = os.path.join(tmpdir, "testkey.pem")
    get_test_settings = settings_factory(EC2_KEY_FILE_PATH=keypath)
    monkeypatch.setattr(ec2, "get_settings", get_test_settings)

    client = boto3.client("ec2", region_name="ap-southeast-2")
    client.create_key_pair(KeyName="testkey")

    with pytest.raises(SystemExit):
        ec2._setup_private_key(client)


_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0dQefaITE7IPJyjT1VIFK91p7n+QokFMQ691H5pemxuXGAIy
Yqfx5ViHx6i59nj4l+7JOx8hP3MzB7rWp/zhSAElmeDIrOHxcFycMGPCDiaG44mf
dm5DTa7FiwgsNXsjLg2wDsa2YAJcCEBFYBdKNfZ9ql5z8WY6AIQkrG5z4m+g/KyN
ZgYmrE9cxqTcDrK1ixT/eM9zOVJDk13A6+5JnNuP5q8HTRgrdbb8GBfInMOjzdnt
Cocg9HnfNA5aqL/8jxei+Ju1FKKQlFy3PGSTeoRwIBurQqFdH3nhTxjqJiy2RpMz
XaqAupoKLkGTmsCocEhrcaIt3rKhn9ciEOE32wIDAQABAoIBAQCmlV73ovq+Qjjh
f/pde1Z7srbtD/2Fs42Wlu/HfUjqn4bfGq9hv6+9wwFZM80frn6+MGc2NsqwkwbK
dj0A9TTtc2uktN7c0ixaZkvh5vEjRtcEQjiFT5jDTaOrc3uVogMWBuvlb0FPC9CB
BHWPii3ylZTC82XdGqmly0NKWg5Kj6EcPzB5l8aPMGcOxo3O+LnIBmC32IwmF+VA
bbzIurI/btRIDYjWhm+57BC1QJBpN340rrWfqCyzzSGuRiPE+5BomP/gqNzEfGFu
/Ni8EpBoSQC1ZoRTqa0xkN3DUvrywr4EjwhJA2/40sBpcfGQ6/3Lf/CIh4WL85yl
JLPI/V4RAoGBAOnRfWEPQP2rUNdIzKSXFZyYUAeb07gaXbHmKP5SZEGKoUUwIvWm
lSdZrKZg+ldqa0gs9TbGthwXFv+AfFsEWLuSkRhdUbacnEl9BRtuVdkTPxbsNMUJ
Gl0lqVJo1RcPsSvdxJ2C9dPFTKDYk5aKj3TT4k3UHnEFn+drS0FUJGCfAoGBAOW8
A9KFZKJaFc2EoGiQT4VyGrlsnlhHr1Moj7q5nyd7OunHsK5UiMqKfawFBpCRta2R
vAyzrJZ5dP4hkWr0+HkG8xRdd6+o4HiSfAyckr7ga369/0aIVvbeBl6F0xm+ZGRc
FoFYtuUMMpcP+lDt64SFlwhT+fh728PvC9vJ/LNFAoGAO5snDk44MDKzKh6p5K+L
V99QT5A++ejmx8o32xWf70Fq+VtbHip4TY7Dv6prR0uey8iCPpOLqz+Loljb2swR
3sdva7mmchockXNokOSgx/TrGWnfzfcTHHnUX2jQIc/jR56CV/Ehv/nFHh/4B+GM
zqiRQWv40rEvYWxtw9qyZ1sCgYEAxgcnlFR/xqK4oItuajPbGECfYK6MX7SLILea
DW7sDfBffB0x41PjBhQS+DDs07mGTbON0bUfVCYl/tmYrAW2GT0wU6GuBbEgrU43
t/dPV1HD12CXp4jmza3c96WLrmk7yHbIv35lSVMWWLjhINm1ZmpxIjChDNxXN7Hb
Gv4l4bECgYB1lB8PFroJidGcPb43P398jS12i+eDvfsyGNCZKxBkPh6egPq1H3f1
0SuSnLjNcM0w3lhs5wkF9DMlWcqLPb+291jQhyeXgTHQTOlCgF/QaXaNVChC+1N0
OqSBXcNgP22t5tUJydLct7853voGpQzG1zIrYF/XKdnlvHm3PZTxLA==
-----END RSA PRIVATE KEY-----
"""