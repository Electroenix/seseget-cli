from pathlib import Path

from seseget.config.schema import (
    CONFIG_FIELDS,
    build_patch,
    get_ui_schema,
    redact_config,
    validate_changes,
    validate_config,
)


def test_readme_lists_all_config_fields():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(
        encoding="utf-8"
    )

    for path in CONFIG_FIELDS:
        assert f"`{path}`" in readme


def test_schema_has_labels_descriptions_and_secret_metadata():
    schema = get_ui_schema()

    assert schema["sections"]["bika"]["label"] == "哔咔"
    assert schema["fields"]["bika.password"]["label"] == "密码"
    assert schema["fields"]["bika.password"]["secret"] is True
    assert schema["fields"]["download.max_history"]["description"]


def test_validate_config_preserves_legacy_extras_for_migration():
    validated = validate_config(
        {
            "bika": {"token": "legacy-token", "nonce": ""},
            "jmcomic": {"login": {"cookie": "legacy-cookie"}},
        }
    )

    assert validated["bika"]["token"] == "legacy-token"
    assert validated["bika"]["nonce"] == ""
    assert validated["jmcomic"]["login"]["cookie"] == "legacy-cookie"


def test_redact_config_hides_secrets_and_session_fields():
    config = {
        "bika": {
            "username": "user",
            "password": "secret-password",
            "token": "session-token",
        },
        "bilibili": {"cookie": "secret-cookie"},
        "download": {"max_history": 200},
    }

    visible, secret_fields, configured = redact_config(config)

    assert visible["bika"]["username"] == "user"
    assert visible["bika"]["password"] == ""
    assert "token" not in visible["bika"]
    assert visible["bilibili"]["cookie"] == ""
    assert visible["download"]["max_history"] == 200
    assert set(secret_fields) == {
        "bika.password",
        "jmcomic.login.password",
        "bilibili.cookie",
        "hanime.cookie",
    }
    assert "bika.password" in configured
    assert "bilibili.cookie" in configured


def test_redact_config_omits_session_fields_even_if_present():
    visible, _, _ = redact_config(
        {
            "bika": {"nonce": "", "token": "token"},
            "jmcomic": {"login": {"cookie": "cookie"}},
        }
    )

    assert "bika" not in visible
    assert "jmcomic" not in visible


def test_validate_changes_accepts_known_types():
    config = {
        "download": {
            "max_history": 200,
            "save_source_info": False,
            "comic": {"format": ["cbz"]},
        }
    }

    assert validate_changes(
        config,
        {
            "download.max_history": 100,
            "download.save_source_info": True,
            "download.comic.format": ["epub"],
        },
    ) is None


def test_validate_changes_rejects_unknown_session_and_invalid_types():
    config = {
        "bika": {"password": "p", "token": "t"},
        "download": {"max_history": 200},
    }

    assert "未知配置字段" in validate_changes(config, {"unknown.key": "x"})
    assert "会话字段" in validate_changes(config, {"bika.token": "x"})
    assert "必须是整数" in validate_changes(config, {"download.max_history": "200"})
    assert "必须大于等于 1" in validate_changes(config, {"download.max_history": 0})
    assert "必须是整数" in validate_changes(config, {"download.max_history": True})


def test_build_patch_builds_nested_structure():
    assert build_patch(
        {
            "download.max_history": 10,
            "bika.password": "new",
        }
    ) == {
        "download": {"max_history": 10},
        "bika": {"password": "new"},
    }
