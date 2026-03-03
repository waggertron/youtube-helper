from click.testing import CliRunner

from youtube_helper.cli.main import cli


def test_analyze_prints_coming_soon():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "some_video"])
    assert result.exit_code == 0
    assert "coming soon" in result.output.lower()
