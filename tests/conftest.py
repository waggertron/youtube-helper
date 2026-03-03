import pytest
from click.testing import CliRunner

from youtube_helper.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cli_invoke(runner):
    def invoke(*args, **kwargs):
        return runner.invoke(cli, args, catch_exceptions=False, **kwargs)
    return invoke
