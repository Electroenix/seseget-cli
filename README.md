# seseget-cli
基于python开发的视频/漫画资源下载工具

## 功能
- 使用命令行+资源页面url下载资源文件
- 支持自动刮削资源元数据，可方便的导入媒体库管理
- 当前支持站点：
  - 视频资源：Hanime.me, Bilibili, Youtube, Twitter
  - 漫画资源：哔咔, JMComic, Wnacg

## 媒体库支持
本工具下载资源会自动刮削页面元数据，可以方便的导入媒体库  

- 支持媒体库：
  - 视频：emby, 群晖VideoStation
  - 漫画：komga

## 部署

### 环境要求：
- **Python3.11**
- **[FFmpeg](https://www.ffmpeg.org/)**: 用于处理视频，下载bilibili/youtube/twitter视频需要安装此软件，并配置好环境变量

### 安装：
#### 1,使用pipenv安装虚拟环境(推荐)
```bash
# 安装Pipenv（如未安装）
pip install pipenv

# 初始化虚拟环境并安装依赖
pipenv sync

# 进入虚拟环境(后续使用工具都要进入虚拟环境使用)
pipenv shell
```

#### 2,不使用pipenv安装依赖
```bash
pip install -r requirements.txt
```

## 使用
一般指定下载站点和资源页面url就可以下载资源 (一些站点需要登录，请查看**配置**章节先修改相关配置)
```text
seseget.py -s [SITE] url

SITE     下载资源的站点，支持以下值：bika/hanime/wnacg/bilibili/youtube/jmcomic  
url         下载资源的url，资源详情页面的url，如视频播放页/漫画详情页
```

更多参数用法请参照下面的参数说明:
```text
seseget.py -h
usage: seseget.py [-h] [-s SITE] [-c CHAPTER] [--no-download] url [url ...]

positional arguments:
  url                   url，可接受多个url

options:
  -h, --help            show this help message and exit
  -s SITE, --site SITE  站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]
  -c CHAPTER, --chapter CHAPTER
                        章节号，仅bika支持，指定下载章节号，多个章节请使用逗号分隔, 未指定章节则下载全部章节
  --no-download         不下载资源，仅显示资源信息
```

## 配置
初次运行脚本会生成```conf/conf.yaml```文件，或者手动复制项目目录下的```core/config/default_conf.yaml```到```conf/conf.yaml```，修改文件中配置并保存，下次运行将会应用新的配置
### 全局配置
```yaml
common:
  # 设置代理地址, 默认使用系统代理
  # 格式: [协议]://[主机]:[端口]
  # 如 http://127.0.0.1:7890
  proxy: ""
```

### 哔咔配置
哔咔需要登录才能下载，在```conf/conf.yaml```中设置用户名和密码
```yaml
bika:
  username: ""  # 用户名
  password: ""  # 密码
  # 以下为保存的cookie数据，无需修改
  nonce: ""
  token: ""
```

### JMcomic配置
```yaml
jmcomic:
  login:
    username: ""  # 用户名
    password: ""  # 密码
    # 以下为保存的cookie数据，无需修改
    cookie: ""
```

### bilibili配置
bilibili还不支持用户名密码登录功能，如需登录，需要自己设置cookie
```yaml
bilibili:
  # B站cookie需要自己配置
  cookie: ""
```

### 下载配置
```yaml
download:
  # true: 会在下载目录下生成source.txt文件保存下载资源的来源信息，false: 不生成source.txt
  save_source_info: false

  # 漫画下载配置
  comic:
    # true: 保留下载的原始图片，false: 不保留图片
    leave_images: false
    # 漫画文件保存格式
    format:
    - cbz
    #- epub

  # 视频下载配置
  video:
    # 视频元数据文件格式
    metadata_file:
    - nfo    # 常用格式，支持emby识别
    #- vsmeta    # 支持群晖VideoStation识别
```

## 文件说明

文件默认下载到与脚本同级的`data`目录下，以下是下载完成后的文件及目录说明
- 下载视频
```text
data                                # 下载目录
└── site                         # 站点目录
    └── artist                      # 作者目录
        └── video                   # 视频目录
            ├── video.mp4           # 视频文件
            ├── video.nfo           # 元数据文件
            ├── fanart.jpg          # 背景图片
            ├── poster.jpg          # 封面图片
            └── source.txt          # 下载来源信息
```
> - 将artist目录复制到媒体库即可自动识别
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