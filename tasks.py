"""
Invoke tasks, view with `inv -l`
"""
from invoke import task


@task
def lint(c):
    """Run run linting"""
    c.run(f"mypy .")
    c.run(f"black --check .", pty=True)


@task
def format(c):
    """Run run formatting"""
    c.run(f"black .", pty=True)
