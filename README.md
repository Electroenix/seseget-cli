# seseget
支持多站点的媒体资源下载工具

## 功能
- 下载指定媒体资源（支持视频/漫画）
- 支持站点：
  - 视频站：Hanime.me, Bilibili, Youtube, Twitter
  - 漫画站：哔咔, JMComic, Wnacg

- 下载时自动刮削站点上的媒体信息，导入媒体库自动填充信息

- 支持媒体库：
  - 视频：emby, jellyfin, 群晖VideoStation
  - 漫画：komga
  >- 以上媒体库已经验证过完全适配，其它的可能也支持
  >- 漫画支持保存为标准格式，一般的阅读软件也是可以识别的

## 使用方式

### 命令行模式
#### 环境要求：
- **Python3.11+**

#### 安装：
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt

# Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 使用
指定资源站点和资源页面url即可使用，如下： (一些站点需要登录，请查看**配置**章节先修改相关配置)

```bash
# Windows
.venv\Scripts\activate.bat  # 激活环境
python seseget -s hanime https://hanime1.me/watch?v=xxxxxxx

# Linux
source .venv/bin/activate  # 激活环境
python seseget -s hanime https://hanime1.me/watch?v=xxxxxxx
```

更多参数用法请参照下面的参数说明:

```bash
python seseget -h
usage: seseget [-h] [-s SITE] [-c CHAPTER] [--no-download] url [url ...]

positional arguments:
  url                   url，可接受多个url

options:
  -h, --help            show this help message and exit
  -s SITE, --site SITE  站点名，支持['bika', 'bilibili', 'hanime', 'jmcomic', 'twitter', 'wnacg', 'youtube']
  -c CHAPTER, --chapter CHAPTER
                        章节号，指定漫画下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节
  --no-download         不下载资源，仅显示资源信息
```

### Web面板模式

新增了Web操作面板功能，使用起来更加方便

#### 环境要求
- Python 3.11+
- Node.js 22+

#### 一键安装运行
Windows运行根目录下的 ```start.bat```, Linux 运行 ```start.sh``` 脚本，将会自动安装依赖并运行

#### 手动安装
安装依赖
```bash
# 1, 激活python虚拟环境

# Windows
python -m venv .venv
.venv\Scripts\activate.bat

# Linux
python -m venv .venv
source .venv/bin/activate

# 2, 安装python依赖
pip install -r requirements.txt -r web_app/requirements.txt

# 3, 安装node依赖
cd web_frontend
npm install

# 4, 编译静态文件
npm run build
```

启动Web应用:

```bash
python -m web_app --prod --host 0.0.0.0 --port 12450
```

#### 访问
web应用启动后会在终端显示 Auth Token 和服务器地址，浏览器中访问对应地址，并输入 Auth Token, 即可开始使用
```
==================================================
  [Production Mode]  Flask + SocketIO
  debug=False
  Listening on http://0.0.0.0:12450
==================================================

==================================================
  [Auth Token]: xxxxxxxxxxxxxxxxxxxxxx
==================================================

 * Serving Flask app 'web_app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:12450
 * Running on http://192.168.xxx.xxx:12450
```

## 配置
初次运行脚本会生成```conf/conf.yaml```文件，或者手动复制项目目录下的```seseget/config/default_conf.yaml```到```conf/conf.yaml```，修改文件中配置并保存，下次运行将会应用新的配置，更多配置说明见 [配置文件](seseget/config/default_conf.yaml)


## 依赖项说明
- **Python** 必须安装，推荐版本3.11+
- **Node.js** 使用web面板必须安装，推荐版本22+
- **[FFmpeg](https://www.ffmpeg.org/)**: 用于处理视频，下载bilibili/youtube/twitter视频需要安装此软件，并配置好环境变量


## 下载文件说明

文件默认下载到与脚本同级的`data`目录下，以下是下载完成后的文件及目录说明
- 下载视频
```text
data                                # 下载目录
└── site                         # 站点目录
    └── series                      # 系列目录
        └── video                   # 视频目录
            ├── video.mp4           # 视频文件
            ├── video.nfo           # 元数据文件
            ├── fanart.jpg          # 背景图片
            ├── poster.jpg          # 封面图片
            └── source.txt          # 下载来源信息
```
> - 将series目录复制到媒体库即可自动识别
> - 群晖VideoStation默认识别与视频同名的图片文件作为封面，需要在`设置->高级->视频封面设置`中勾选`将以下文件名的图像设为视频封面`，并在`文件名`中添加poster.jpg

- 下载漫画
```text
data                                # 下载目录
└── site                         # 站点目录
    └── comic                       # 漫画目录
        ├── comic_001.cbz           # 第一话
        ├── comic_002.cbz           # 第二话
            ...
        ├── comic_xxx.cbz           # 第xxx话
        └── source.txt              # 下载来源信息
```
> - 将comic目录复制到媒体库，komga需要在应用内手动更新识别