import xml.etree.ElementTree as ET
import zipfile

from seseget.output.comic.cbz import write_cbz
from seseget.output.comic.comic_info import write_comic_info_xml
from seseget.output.comic.epub import write_epub


def test_write_comic_info_xml_escapes_metadata(tmp_path, comic_metadata):
    write_comic_info_xml(str(tmp_path), comic_metadata)

    root = ET.parse(tmp_path / "ComicInfo.xml").getroot()
    assert root.findtext("Series") == comic_metadata.series
    assert root.findtext("Title") == comic_metadata.title
    assert root.findtext("Writer") == comic_metadata.creator
    assert root.findtext("Summary") == comic_metadata.description
    assert root.findtext("Tags") == "tag & one,tag <two>"
    assert root.findtext("Year") == "2024"


def test_write_cbz_contains_images_and_comic_info(tmp_path, comic_images, comic_metadata):
    write_cbz(str(tmp_path), "chapter", str(comic_images), comic_metadata)

    cbz_path = tmp_path / "chapter.cbz"
    assert cbz_path.is_file()

    with zipfile.ZipFile(cbz_path) as cbz:
        names = set(cbz.namelist())
        assert "ComicInfo.xml" in names
        assert "00001.jpg" in names
        assert "00002.jpg" in names
        root = ET.fromstring(cbz.read("ComicInfo.xml"))
        assert root.findtext("Title") == comic_metadata.title


def test_write_epub_is_valid_and_escaped(tmp_path, comic_images, comic_metadata):
    write_epub(str(tmp_path), "chapter", str(comic_images), comic_metadata)

    epub_path = tmp_path / "chapter.epub"
    assert epub_path.is_file()

    with zipfile.ZipFile(epub_path) as epub:
        assert epub.read("mimetype") == b"application/epub+zip"
        xml_names = [
            name
            for name in epub.namelist()
            if name.endswith((".xml", ".opf", ".xhtml"))
        ]
        for name in xml_names:
            ET.fromstring(epub.read(name))

        opf = ET.fromstring(epub.read("OEBPS/content.opf"))
        dc = {"dc": "http://purl.org/dc/elements/1.1/"}
        assert opf.findtext(".//dc:title", namespaces=dc) == comic_metadata.title
        assert opf.findtext(".//dc:creator", namespaces=dc) == comic_metadata.creator
        assert opf.findtext(".//dc:subject", namespaces=dc) == comic_metadata.subjects[0]
