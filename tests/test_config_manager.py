from seseget.config.config_manager import (
    ObservableDict,
    _merge_missing_defaults,
    _update_nested_dict,
)


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


def test_update_nested_dict_ignores_unknown_keys():
    target = {"download": {"save_source_info": False}}
    source = {"download": {"save_source_info": True, "new_key": 1}, "unknown": 2}

    _update_nested_dict(target, source)

    assert target == {"download": {"save_source_info": True}}


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


def test_observable_dict_replaces_lists_in_origin_data():
    saved = []

    def save_callback():
        saved.append(True)

    config = ObservableDict(
        save_callback,
        {"download": {"comic": {"format": ["cbz", "epub"]}}},
    )

    config["download"]["comic"]["format"] = ["cbz"]

    assert config.origin_data["download"]["comic"]["format"] == ["cbz"]
    assert config["download"]["comic"]["format"] == ["cbz"]
    assert saved


def test_observable_dict_update_syncs_origin_data():
    config = ObservableDict(lambda: None, {"download": {"max_history": 200}})

    config.update({"download": {"max_history": 20}})

    assert config.origin_data["download"]["max_history"] == 20
    assert config["download"]["max_history"] == 20
