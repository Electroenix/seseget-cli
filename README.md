# seseget-cli
基于python开发的视频/漫画资源下载工具

## 功能
- 使用命令行+资源页面url下载资源文件
- 支持自动刮削资源元数据，可方便的导入媒体库管理
- 当前支持站点：
  - 视频资源：Hanime.me, Bilibili, Youtube
  - 漫画资源：哔咔, JMComic, Wnacg

## 媒体库支持
本工具下载资源会自动刮削页面元数据，可以方便的导入媒体库  

### 支持媒体库：
- 视频：emby, 群晖video station
- 漫画：komga

其它媒体库没有用过，暂不知支持情况

### 元数据文件格式: 
- 视频：.nfo，.vsmeta
- 漫画：元数据保存在漫画epub文件中

## 部署

### 环境要求：
- Python3.11
- ffmpeg (某些视频处理需要使用)

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

#### 2,不使用虚拟环境直接安装依赖
```bash
pip install -r requirements.txt
```

## 使用
一般执行下面命令下载资源 (一些站点需要登录，请查看**配置**步骤先进行相关配置)
```
seseget.py -s [站点名] url

[站点名]  下载资源的站点，支持以下值：bika/hanime/wnacg/bilibili/youtube/jmcomic  
url       下载资源的url，资源详情页面的url，如视频播放页/漫画详情页
```

详细参数
```
usage: seseget.py [-h] [-s STATION] [-c CHAPTER] url

positional arguments:
  url                   source url

options:
  -h, --help            show this help message and exit
  -s STATION, --station STATION
                        站点名，支持[bika/hanime/wnacg/bilibili/youtube/jmcomic]
  -c CHAPTER, --chapter CHAPTER
                        章节号，仅bika支持，设置下载章节号，支持多个章节，使用逗号分隔
```

## 配置
脚本首次运行会生成```conf/conf.json```文件，在文件中修改配置
### 代理配置
一些网站可能需要代理访问，可以在这里设置
```
"common": {
  "proxy": {
    "address": "",           # 设置代理地址，如http://127.0.0.1:7890
    "proxy_enable": false    # true:使用代理, false:不使用代理
  }
}
```

### 哔咔配置
哔咔需要登录才能下载，在```conf/conf.json```中设置用户名和密码
```
"bika": {
  "username": "",    # 用户名
  "password": "",    # 密码
  # 下面是cookie相关，登录后会自动保存
  "nonce": "",
  "token": ""
},
```

### JMcomic配置
```
"jmcomic": {
  "login": {
    "username": "",    # 用户名
    "password": "",    # 密码
    "cookie": ""       # cookie，登录后自动保存
  }
},
```

### bilibili配置
bilibili还不支持用户名密码登录功能，如需登录，需要自己设置cookie
```
"bilibili": {
  "cookie": ""
},
```

### 下载配置
```
"download": {
  "comic": {
    "leave_images": false    # true:漫画文件生成后保留下载的图片文件，false:不保留图片
  }
}
```
