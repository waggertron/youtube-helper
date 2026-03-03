from youtube_helper.config.settings import Settings


class TestSettings:
    def test_default_config_dir(self):
        settings = Settings()
        assert ".youtube-helper" in str(settings.config_dir)

    def test_custom_config_dir(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert settings.config_dir == tmp_path

    def test_db_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.db_path).endswith("youtube-helper.db")

    def test_credentials_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.credentials_path).endswith("credentials.json")

    def test_client_secret_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.client_secret_path).endswith("client_secret.json")

    def test_token_path(self, tmp_path):
        settings = Settings(config_dir=tmp_path)
        assert str(settings.token_path).endswith("token.pickle")

    def test_ensure_dirs(self, tmp_path):
        config_dir = tmp_path / "new_dir"
        settings = Settings(config_dir=config_dir)
        settings.ensure_dirs()
        assert config_dir.exists()


class TestAuthCli:
    def test_auth_status(self, runner):
        from youtube_helper.cli.main import cli

        result = runner.invoke(cli, ["auth", "status"])
        assert result.exit_code == 0
        assert "Authentication Status" in result.output
