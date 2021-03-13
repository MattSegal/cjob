"""
Test that we're mangling instance names correctly.
"""
import pytest

from cjob import ec2


JOB_NAMES = ["hey", "HELLO", "131@23!-123@@@- -!", ""]


@pytest.mark.parametrize("name", JOB_NAMES)
def test_job_prefix(name):
    name = "hey"
    assert ec2.JOB_PREFIX == "cjob-"
    assert not ec2.has_job_prefix(name)
    jobname = ec2.add_job_prefix(name)
    assert ec2.has_job_prefix(jobname)
    assert jobname == f"cjob-{name}"
    newname = ec2.strip_job_prefix(jobname)
    assert newname == name
    assert not ec2.has_job_prefix(newname)
