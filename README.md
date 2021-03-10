# Cloud Jobs in AWS (cjob)

![Automated Tests](https://github.com/MattSegal/cjob/workflows/Automated%20Tests/badge.svg)

This tool is built for people who are doing scientific computing or machine learning and want quickly get their code running on a big server using Amazon Web Services (AWS).

It is a Python-based command-line tool for running jobs on temporary [AWS EC2](https://aws.amazon.com/ec2/) instances (which are Linux computers in the cloud).

In general, when running a job this tool will:

- Create a new EC2 instance for you (ie. a Linux server)
- Run your Python code on the instance
- Destroy the EC2 instance

That's basically it. The cost of using an EC2 instance is proportional to the amount of time that it is running. This tool seeks to minimize this time by only running an instance when it's necessary.

## Helpful Tools

This tool can be combined with:

- [Fabric](http://www.fabfile.org/) to help you run scripts on the server; and
- [Packer](https://www.packer.io/) to help you set up the server more quickly

See the tutorials (below) for how to use these tools (cjob, Fabric, Packer) together.

## Installation and Setup

Install the "cjob" package from PyPI

```bash
pip install cjob
```

Add a config file named `cjob.yml` to your project. A minimal config could look like this:

```yaml
AWS_REGION: ap-southeast-2
AWS_PROFILE: default
EC2_INSTANCE_TYPE: r5.2xlarge
EC2_KEY_FILE_PATH: ~/.ssh/wizard.pem
```

See the Configuration section below for more details.

You can verify that these settings are working with `cjob settings`. You can see all command line options with `cjob --help`. See the tutorials (below) for more details on usage.

## Tutorials

- (todo) Running a simple job manually
- (todo) Running a simple job automatically
- (todo) Building an Amazon Machine Image (AMI) to speed up setup
- (todo) Running a PyTorch neural net on a GPU in the cloud
- (todo) Run a job using GitHub Actions

## Configuration

This tool is configured using a mandatory config file called "cjob.yml". [See here](cjob.example.yml) for a full description of the configuration options. **I recommend you look over this example file before using the tool**.

## Infrastructure

what this will do to your infrastructure

- old AMIs
- old volumes
- old instances

## Development

[Poetry](https://python-poetry.org/) is used for packaging and dependency management.
Some common things to do as a developer working on this codebase:

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
