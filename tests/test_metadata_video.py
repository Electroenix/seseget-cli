import xml.etree.ElementTree as ET

from seseget.output.video import VIDEO_METADATA_WRITERS
from seseget.output.video.nfo import write_nfo
from seseget.output.video.vsmeta import write_vsmeta


def test_video_writers_registered():
    assert {"nfo", "vsmeta"}.issubset(VIDEO_METADATA_WRITERS)


def test_write_nfo_escapes_metadata(tmp_path, video_metadata):
    write_nfo(str(tmp_path), "video", video_metadata)

    nfo_path = tmp_path / "video.nfo"
    assert nfo_path.is_file()

    root = ET.parse(nfo_path).getroot()
    assert root.findtext("title") == video_metadata.sub_title
    assert root.findtext("originaltitle") == video_metadata.title
    assert root.findtext("year") == "2024"
    assert root.findtext("plot") == video_metadata.describe
    assert [item.text for item in root.findall("tag")] == video_metadata.tag_list


def test_write_vsmeta_valid_year(tmp_path, video_metadata):
    write_vsmeta(str(tmp_path), "video", video_metadata)

    path = tmp_path / "video.mp4.vsmeta"
    assert path.is_file()
    data = path.read_bytes()
    assert bytes.fromhex("28") in data
    assert len(data) > 0


def test_write_vsmeta_invalid_year_does_not_fail(tmp_path, video_metadata):
    for year in ("", "not-a-year", "1000"):
        video_metadata.year = year
        write_vsmeta(str(tmp_path), f"video-{year or 'empty'}", video_metadata)

    assert (tmp_path / "video-empty.mp4.vsmeta").is_file()
    assert (tmp_path / "video-not-a-year.mp4.vsmeta").is_file()
    assert (tmp_path / "video-1000.mp4.vsmeta").is_file()

    data = (tmp_path / "video-not-a-year.mp4.vsmeta").read_bytes()
    assert bytes.fromhex("28") not in data


def test_write_vsmeta_with_background(tmp_path, video_metadata):
    background = tmp_path / "bg.jpg"
    background.write_bytes(b"\xff\xd8fake-jpeg")
    video_metadata.back_ground_path = str(background)

    write_vsmeta(str(tmp_path), "with-bg", video_metadata)

    assert (tmp_path / "with-bg.mp4.vsmeta").stat().st_size > 0
