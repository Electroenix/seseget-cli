from seseget.config.config_manager import (
    _merge_missing_defaults,
    _update_nested_dict,
)
from seseget.config.schema import validate_config


def test_update_nested_dict_merges_dicts_and_replaces_lists():
    target = {
        "download": {
            "comic": {"format": ["cbz", "epub"], "leave_images": False},
            "video": {"metadata_file": ["nfo", "vsmeta"]},
        }
    }
    source = {
        "download": {
            "comic": {"format": ["cbz"]},
            "video": {"metadata_file": ["nfo"]},
        }
    }

    _update_nested_dict(target, source)

    assert target["download"]["comic"]["format"] == ["cbz"]
    assert target["download"]["comic"]["leave_images"] is False
    assert target["download"]["video"]["metadata_file"] == ["nfo"]


def test_update_nested_dict_adds_new_keys():
    target = {"download": {"save_source_info": False}}
    source = {"download": {"save_source_info": True, "new_key": 1}, "unknown": 2}

    _update_nested_dict(target, source)

    assert target == {
        "download": {"save_source_info": True, "new_key": 1},
        "unknown": 2,
    }


def test_merge_missing_defaults_keeps_user_values_and_adds_new_keys():
    target = {
        "download": {
            "max_history": 50,
            "comic": {"format": ["cbz"]},
        }
    }
    defaults = {
        "download": {
            "max_history": 200,
            "comic": {"format": ["cbz"], "leave_images": False},
            "video": {"metadata_file": ["nfo"]},
        }
    }

    _merge_missing_defaults(target, defaults)

    assert target["download"]["max_history"] == 50
    assert target["download"]["comic"] == {
        "format": ["cbz"],
        "leave_images": False,
    }
    assert target["download"]["video"] == {"metadata_file": ["nfo"]}


def test_validate_config_applies_schema_types_and_defaults():
    validated = validate_config(
        {
            "download": {"max_history": 50},
            "sites": {"bika": {"username": "user"}},
        }
    )

    assert validated["download"]["max_history"] == 50
    assert validated["download"]["comic"]["format"] == ["cbz"]
    assert validated["sites"]["bika"]["username"] == "user"
    assert validated["sites"]["bika"]["password"] == ""
