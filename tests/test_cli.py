def test_cli_help(cli_invoke):
    result = cli_invoke("--help")
    assert result.exit_code == 0
    assert "YouTube Helper" in result.output


def test_cli_version(cli_invoke):
    result = cli_invoke("--version")
    assert result.exit_code == 0
    assert "0.1.0" in result.output
