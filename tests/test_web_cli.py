from youtube_helper.cli.main import cli


class TestWebCli:
    def test_web_command_exists(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert result.exit_code == 0
        assert "Start the web dashboard" in result.output

    def test_web_command_has_port_option(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert "--port" in result.output

    def test_web_command_has_no_browser_option(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert "--no-browser" in result.output
