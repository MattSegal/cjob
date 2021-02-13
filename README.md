# Cloud Job (cjob) for AWS

This is a little CLI framework for running jobs on transient [AWS EC2](https://aws.amazon.com/ec2/?ec2-whats-new.sort-by=item.additionalFields.postDateTime&ec2-whats-new.sort-order=desc) instances. By "transient" I mean that the EC2 instances are created when you start running the job, and they are destroyed when the job finishes running. It's like a crappier version of [ray](https://ray.io/) except maybe a little easier to use.

# Development

Some common things to do as a developer:

```bash
# Install requirements
poetry install
# Get a virtualenv for running other stuff
poetry shell
# Publish to PyPI
poetry publish
# Add a new package
poetry add
# Run tests
pytest -vv
# Format Python code
inv format
# Check for static typing issues / lint issues
inv lint
```
