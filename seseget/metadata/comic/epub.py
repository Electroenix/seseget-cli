import os
import uuid
import zipfile
from tempfile import TemporaryDirectory
from pathlib import Path
import shutil
from datetime import datetime, timezone
from PIL import Image

from . import ComicMetaData
from ...utils.trace import logger


# 是否生成封面页
MAKE_COVER_PAGE = False

# 翻页方向: rtl - 右至左    ltr - 左至右
PAGE_PROGRESSION_DIRECTION = "ltr"


class EpubGenerator:

    MEDIA_TYPE_MAP = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
    }

    def __init__(self,
                 output_dir: str,
                 image_dir: str,
                 metadata: ComicMetaData):
        self.output_dir = output_dir
        self.image_dir = image_dir
        self.metadata = metadata
        self.image_files = []
        self.page_files = []
        self.cover_image_file = {}
        self.cover_page_file = ""
        self.package_dir = ""
        self.path = {}

    def _path_config(self):
        self.path = {
            "mimetype": str(Path(self.package_dir) / "mimetype"),
            "container_xml": str(Path(self.package_dir) / "META-INF/container.xml"),
            "opf": str(Path(self.package_dir) / "OEBPS/content.opf"),
            "nav": str(Path(self.package_dir) / "OEBPS/nav.xhtml"),
            "style_css": str(Path(self.package_dir) / "OEBPS/Styles/style.css"),
            "pages": str(Path(self.package_dir) / "OEBPS/Text"),
            "images": str(Path(self.package_dir) / "OEBPS/Images"),
        }

        (Path(self.package_dir) / "META-INF").mkdir()
        (Path(self.package_dir) / "OEBPS").mkdir()
        (Path(self.package_dir) / "OEBPS/Images").mkdir()
        (Path(self.package_dir) / "OEBPS/Text").mkdir()
        (Path(self.package_dir) / "OEBPS/Styles").mkdir()

    def _collect_images(self):
        source_path = Path(self.image_dir)
        target_path = Path(self.path["images"])

        # 确保目标目录存在
        target_path.mkdir(parents=True, exist_ok=True)

        # 支持的图片格式
        image_extensions = self.MEDIA_TYPE_MAP.keys()

        # 收集所有图片文件
        image_files_set = set()
        for ext in image_extensions:
            for file_path in source_path.rglob(f"*{ext}"):
                image_files_set.add(file_path.resolve())

            for file_path in source_path.rglob(f"*{ext.upper()}"):
                image_files_set.add(file_path.resolve())

        # 按文件名排序
        image_files = sorted(image_files_set, key=lambda x: x.name.lower())

        # 复制文件, 并按序号命名
        self.image_files = []
        for index, src_file in enumerate(image_files):
            img = Image.open(src_file)
            img_format = img.format.lower()  # 获取图片实际格式

            # 根据实际格式修改后缀名
            img_suffix = f".{img_format}"
            img_path = target_path / f"img-{index}{img_suffix}"

            shutil.copy2(src_file, img_path)

            self.image_files.append({
                "filename": img_path.name,
                "media_type": self.MEDIA_TYPE_MAP[img_suffix],
                "height": img.height,
                "width": img.width,
            })

        # 复制第一张图作为封面
        cover_image = (target_path / self.image_files[0]["filename"]).with_stem("cover")
        shutil.copy2(target_path / self.image_files[0]["filename"], cover_image)
        self.cover_image_file = {
            "filename": cover_image.name,
            "media_type": self.MEDIA_TYPE_MAP[cover_image.suffix],
            "height": self.image_files[0]["height"],
            "width": self.image_files[0]["width"],
        }

    def _make_mimetype(self):
        with open(self.path["mimetype"], "w", encoding='utf-8') as f:
            f.write("application/epub+zip")

    def _make_container_xml(self):
        with open(self.path["container_xml"], "w", encoding='utf-8') as f:
            f.write(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf"
            media-type="application/oebps-package+xml" />
    </rootfiles>
</container>""")

    def _make_cover_page(self):
        """创建专门的封面XHTML页面（作为第一页）"""
        if not self.image_files:
            return
        cover_file = Path(self.path["pages"]) / "cover.xhtml"

        with open(cover_file, 'w', encoding='utf-8') as f:
            f.write(f'''\
<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head>
    <title>Cover</title>
    <meta name="viewport" content="width={self.cover_image_file["width"]}, height={self.cover_image_file["height"]}"/>
    <meta charset="utf-8"/>
    <link rel="stylesheet" type="text/css" href="../Styles/style.css"/>
  </head>
  <body epub:type="cover">
    <div class="comic-page comic-page-cover">
      <img src="../Images/{self.cover_image_file['filename']}" alt="cover" class="comic-img"/>
    </div>
  </body>
</html>''')
            self.cover_page_file = cover_file.name

    def _make_page(self, order: int, image_file: dict):
        page_file = Path(self.path["pages"]) / f"page-{order}.xhtml"

        # 获取第一个图片的尺寸作为固定尺寸
        content_width = self.image_files[0]["width"] if self.image_files else 1200
        content_height = self.image_files[0]["height"] if self.image_files else 1600

        with open(str(page_file), "w", encoding='utf-8') as f:
            f.write(f"""\
<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head>
    <title>Page #{order}</title>
    <meta name="viewport" content="width={content_width}, height={content_height}"/>
    <meta charset="utf-8"/>
    <link rel="stylesheet" type="text/css" href="../Styles/style.css"/>
  </head>
  <body>
    <div class="comic-page comic-page-content">
      <img src="../Images/{image_file["filename"]}" alt="comic page #{order}" class="comic-img"/>
    </div>
  </body>
</html>""")
            self.page_files.append(page_file.name)

    def _make_style_css(self):
        with open(self.path["style_css"], "w", encoding='utf-8') as f:
            f.write("""\
html, body {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.comic-page {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
.comic-page-cover {
  margin: 0;
  padding: 0;
}
.comic-page-content {
  border: 10px solid transparent;
  box-sizing: border-box;
}
.comic-img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}
@page {
  margin: 0;
  padding: 0;
}""")

    def _make_opf(self):
        with open(self.path["opf"], "w", encoding='utf-8') as f:
            f.write(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uuid_id" prefix="rendition: http://www.idpf.org/vocab/rendition/#">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">""")

            # 元数据: 标题
            if self.metadata.title:
                f.write(f"""
    <dc:title id="main-title">{self.metadata.title}</dc:title>""")

            # 元数据: 作者
            if self.metadata.creator:
                f.write(f"""
    <dc:creator id="author">{self.metadata.creator}</dc:creator>""")

            # 元数据: id
            f.write(f"""
    <dc:identifier id="uuid_id">uuid:{uuid.uuid4()}</dc:identifier>""")

            # 元数据: 语言
            if self.metadata.language:
                f.write(f"""
    <dc:language>{self.metadata.language}</dc:language>""")

            # 元数据: 发布日期
            if self.metadata.year and self.metadata.month and self.metadata.day:
                f.write(f"""
    <dc:date>{"-".join([self.metadata.year, self.metadata.month, self.metadata.day])}</dc:date>""")

            # 元数据: 标签
            for subject in self.metadata.subjects:
                f.write(f"""
    <dc:subject>{subject}</dc:subject>""")

            # 元数据增强: 标题
            if self.metadata.title:
                f.write(f"""
    <meta refines="#main-title" property="title-type">main</meta>
    <meta refines="#main-title" property="file-as">{self.metadata.title}</meta>""")

            # 元数据增强: 作者
            if self.metadata.creator:
                f.write(f"""
    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
    <meta refines="#author" property="file-as">{self.metadata.creator}</meta>""")

            # 修改时间
            f.write(f"""
    <meta name="cover" content="cover"/>
    <meta property="dcterms:modified" scheme="dcterms:W3CDTF">{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</meta>""")

            # 系列
            if self.metadata.series:
                f.write(f"""
    <meta property="belongs-to-collection" id="series">{self.metadata.series}</meta>
    <meta refines="#series" property="collection-type">series</meta>
    <meta refines="#series" property="group-position">{self.metadata.number}</meta>""")

            # 版型
            f.write(f"""
    <meta property="rendition:layout">pre-paginated</meta>
    <meta property="rendition:orientation">auto</meta>
    <meta property="rendition:spread">auto</meta>
  </metadata>""")

            f.write(f"""
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="css" href="Styles/style.css" media-type="text/css"/>""")

            # 封面页
            if MAKE_COVER_PAGE:
                f.write(f"""
    <item id="cover-page" href="Text/{self.cover_page_file}" media-type="application/xhtml+xml"/>""")

            # 页面xhtml
            for page_file in self.page_files:
                f.write(f"""
    <item id="{Path(page_file).stem}" href="Text/{page_file}" media-type="application/xhtml+xml"/>""")

            # 封面图片
            f.write(f"""
    <item id="cover" href="Images/{self.cover_image_file["filename"]}" media-type="{self.cover_image_file["media_type"]}" properties="cover-image"/>""")

            # 页面图片
            for image_file in self.image_files:
                f.write(f"""
    <item id="{Path(image_file["filename"]).stem}" href="Images/{image_file["filename"]}" media-type="{image_file["media_type"]}"/>""")

            f.write(f"""
  </manifest>
  <spine page-progression-direction="{PAGE_PROGRESSION_DIRECTION}">""")

            # 阅读顺序
            if MAKE_COVER_PAGE:
                f.write(f"""
    <itemref idref="cover-page"/>""")

            for page_file in self.page_files:
                f.write(f"""
    <itemref idref="{Path(page_file).stem}"/>""")

            f.write(f"""
  </spine>
</package>""")

    def _make_nav(self):
        with open(self.path["nav"], "w", encoding='utf-8') as f:
            f.write(f"""\
<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">
  <head>
    <title>目录</title>
    <meta charset="utf-8"/>
  </head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>目录</h1>
      <ol>""")

            if MAKE_COVER_PAGE:
                f.write(f"""
        <li><a href="Text/{self.cover_page_file}">封面</a></li>""")

            for index, page_file in enumerate(self.page_files):
                f.write(f"""
        <li><a href="Text/{page_file}">第{index + 1}页</a></li>""")

            f.write(f"""
      </ol>
    </nav>
  </body>
</html>""")

    def generate(self, filename: str = None):
        try:
            if not self.output_dir:
                raise ValueError("EPUB输出目录为空!")

            with TemporaryDirectory(prefix="epub-", dir=self.output_dir) as out_dir:
                self.package_dir = out_dir

                # 路径配置
                self._path_config()

                # 收集所有图片
                self._collect_images()

                # 创建必要文件
                self._make_mimetype()
                self._make_container_xml()
                self._make_style_css()

                if MAKE_COVER_PAGE:
                    self._make_cover_page()

                for index, image_file in enumerate(self.image_files):
                    # 创建漫画页，页码从1开始
                    self._make_page(index + 1, image_file)

                self._make_opf()
                self._make_nav()

                if filename is None:
                    filename = Path(self.output_dir) / f"{self.metadata.title}.epub"

                with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as new_zf:
                    for root, dirs, files in os.walk(self.package_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, self.package_dir)
                            new_zf.write(file_path, arcname)
        except Exception as e:
            raise e


def make_epub(save_dir: str, comic_title: str, image_path: str, metadata: ComicMetaData):
    """
    下载的漫画图片合成EPUB电子书文件
    Args:
        save_dir: 漫画保存的目录路径
        comic_title: 漫画名，基于此名字创建文件名
        image_path: 图片文件夹路径
        metadata: 漫画元数据对象

    """
    logger.info("生成EPUB文件中...")

    epub = EpubGenerator(
        output_dir=save_dir,
        image_dir=image_path,
        metadata=metadata
    )

    filename = str(Path(save_dir) / f"{comic_title}.epub")

    try:
        epub.generate(filename)
        logger.info("生成完成, 漫画保存在%s" % filename)
    except Exception:
        logger.error("生成失败")
        raise
