from pathlib import Path

from invoke import Context, task


class Paths:
    repo_root = Path(__file__).parent
    example_tables = repo_root / "example_tables"


def from_repo_root(c: Context):
    return c.cd(Paths.repo_root)


@task
def compile_requirements(c: Context, install=True, upgrade=False):
    with from_repo_root(c):
        upgrade_flag = "--upgrade" if upgrade else ""
        c.run(f"pip-compile {upgrade_flag} -v --strip-extras --extra dev --extra build pyproject.toml", pty=True)
        c.run("mv requirements.txt requirements.dev.txt", pty=True)
        c.run('echo "-e ." >> requirements.dev.txt')
        if install:
            c.run("pip-sync requirements.dev.txt", pty=True)


@task
def bumpver(c: Context, major=False, minor=False, patch=False, dry=False):
    num_set = 0
    flag = ""
    if major:
        flag = "--major"
        num_set += 1
    if minor:
        flag = "--minor"
        num_set += 1
    if patch:
        flag = "--patch"
        num_set += 1
    if num_set != 1:
        raise SystemExit("Must specify exactly one of --major, --minor, --patch")
    with from_repo_root(c):
        dry_flag = ""
        if dry:
            dry_flag = "--dry"
        c.run(f"bumpver update {flag} {dry_flag}", pty=True)


#
# @task
# def build(c: Context, clean=True):
#     with from_repo_root(c):
#         if clean:
#             c.run("rm -rf dist/*")
#         c.run("python -m build")
#         c.run("twine check dist/*")
#
#
# @task
# def publish(c: Context, testpypi=True):
#     if testpypi:
#         testpypi_flag = "-r testpypi"
#     else:
#         testpypi_flag = ""
#     with from_repo_root(c):
#         c.run(f"twine upload {testpypi_flag} dist/*", pty=True)
#


@task
def lint(c: Context, check=False):
    """When cheeck is True, fails instead of fixes"""
    with from_repo_root(c):
        black_flag = "--check" if check else ""
        c.run(f"black src/ tasks.py {black_flag}", pty=True)
        isort_flag = "--check-only" if check else ""
        c.run(f"isort src/ tasks.py {isort_flag}", pty=True)
        ruff_flag = "--exit-non-zero-on-fix" if check else "--fix"
        c.run(f"ruff check src/ tasks.py {ruff_flag}", pty=True)


#
# @task
# def fullrelease(c: Context, major=False, minor=False, patch=False):
#     lint(c, check=True)
#     with from_repo_root(c):
#         c.run("pytest", pty=True)
#     bumpver(c, major, minor, patch)
#     build(c)
#     publish(c, testpypi=False)
#     c.run("git push", pty=True)
#     c.run("git push --tags", pty=True)
