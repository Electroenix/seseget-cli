import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET

from ...metadata.video import VideoMetaData
from ...utils.file_utils import make_filename_valid


def write_nfo(save_dir: str, video_name: str, metadata: VideoMetaData):
    """生成 NFO 元数据文件。"""
    filename = save_dir + '/' + make_filename_valid(f"{video_name}.nfo")
    movie = ET.Element('movie')

    plot = ET.SubElement(movie, 'plot')
    plot.text = metadata.describe

    ET.SubElement(movie, 'outline')

    lockdata = ET.SubElement(movie, 'lockdata')
    lockdata.text = 'false'

    lockedfields = ET.SubElement(movie, 'lockedfields')
    lockedfields.text = 'Name|OriginalTitle|SortName|Studios|Tags'

    title = ET.SubElement(movie, 'title')
    title.text = metadata.sub_title

    originaltitle = ET.SubElement(movie, 'originaltitle')
    originaltitle.text = metadata.title

    year = ET.SubElement(movie, 'year')
    year.text = metadata.year[:4]

    sorttitle = ET.SubElement(movie, 'sorttitle')
    sorttitle.text = metadata.title

    premiered = ET.SubElement(movie, 'premiered')
    premiered.text = metadata.public_time

    releasedate = ET.SubElement(movie, 'releasedate')
    releasedate.text = metadata.public_time

    studio = ET.SubElement(movie, 'studio')
    studio.text = metadata.author

    for t in metadata.tag_list:
        tag = ET.SubElement(movie, 'tag')
        tag.text = t

    # set = ET.SubElement(movie, 'set')
    # collection_name = ET.SubElement(set, 'name')
    # collection_name.text = metadata.artist

    dom = minidom.parseString(ET.tostring(movie))
    with open(filename, 'wb') as f:
        f.write(dom.toprettyxml(encoding='utf-8'))


