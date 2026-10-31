import web_app.api.auth as auth


def test_generated_token_is_printed(monkeypatch, capsys):
    monkeypatch.delenv("SESEGET_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(auth, "web_config", {})
    updates = []
    monkeypatch.setattr(auth.web_config_manager, "update", lambda data: updates.append(data))

    token = auth.init_auth_token()

    assert token
    assert updates == [{"auth_token": token}]
    output = capsys.readouterr().out
    assert f"[Auth Token] generated: {token}" in output
    assert "saved to" in output


def test_env_token_is_not_printed(monkeypatch, capsys):
    monkeypatch.setenv("SESEGET_AUTH_TOKEN", "env-token")
    monkeypatch.setattr(auth, "web_config", {})
    updates = []
    monkeypatch.setattr(auth.web_config_manager, "update", lambda data: updates.append(data))

    token = auth.init_auth_token()

    assert token == "env-token"
    assert updates == [{"auth_token": "env-token"}]
    assert capsys.readouterr().out == ""


def test_file_token_is_not_printed(monkeypatch, capsys):
    monkeypatch.delenv("SESEGET_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(auth, "web_config", {"auth_token": "file-token"})

    token = auth.init_auth_token()

    assert token == "file-token"
    assert capsys.readouterr().out == ""
