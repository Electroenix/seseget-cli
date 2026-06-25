# ============================================================================
# seseget Docker 三阶段构建
# Stage 1: 编译最小化 ffmpeg + ffprobe（Alpine 静态构建）
# Stage 2: 编译 React 前端（Node 22 Alpine）
# Stage 3: Python 3.11 运行时 + 构建完整项目（Debian slim）
# ============================================================================

# ========================== Stage 1: ffmpeg builder ==========================
FROM alpine:3.22 AS ffmpeg-builder

RUN apk add --no-cache \
    gcc g++ make pkgconf nasm xz wget ca-certificates \
    zlib-dev zlib-static \
    openssl-dev openssl-libs-static

# 下载 ffmpeg
ARG FFMPEG_VERSION=7.1.1
RUN wget -q https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz -O /tmp/ffmpeg.tar.xz \
    && cd /tmp && tar xf ffmpeg.tar.xz

WORKDIR /tmp/ffmpeg-${FFMPEG_VERSION}

# --disable-everything + 按需启用，编译出最小静态 ffmpeg/ffprobe
RUN ./configure \
    --disable-everything \
    --enable-static \
    --disable-shared \
    --enable-gpl \
    --enable-version3 \
    --enable-ffmpeg \
    --enable-ffprobe \
    \
    `# === 解封装（demuxer）===` \
    --enable-demuxer=mov,mpegts,concat,aac,mp3,flv,matroska,ogg,wav,webm_dash_manifest \
    `# 封装（muxer）` \
    --enable-muxer=mp4,mov,adts \
    \
    `# === 解码器（decoder）- 仅常见音频格式 ===` \
    --enable-decoder=aac,mp3,mp2,opus,vorbis,flac,pcm_s16le,pcm_s24le \
    --enable-decoder=ac3,eac3,alac,wmav1,wmav2 \
    `# 编码器（encoder）- 仅 AAC ===` \
    --enable-encoder=aac \
    \
    `# === 解析器（parser）===` \
    --enable-parser=h264,hevc,aac,mpegaudio,opus,vorbis,flac \
    \
    `# === 协议（protocol）===` \
    --enable-protocol=file,concat,http,https,pipe,tcp,crypto,hls \
    \
    `# === 比特流过滤器（BSF）===` \
    --enable-bsf=h264_mp4toannexb,hevc_mp4toannexb,aac_adtstoasc,extract_extradata,filter_units \
    \
    `# === 滤镜（filter）- 音频重采样必备 ===` \
    --enable-filter=aresample,aformat,anull,atrim,asetpts \
    \
    `# === 基础组件 ===` \
    --enable-avformat \
    --enable-avcodec \
    --enable-avutil \
    --enable-avfilter \
    --enable-swresample \
    --enable-swscale \
    \
    `# === 静态链接 ===` \
    --enable-zlib \
    --enable-openssl \
    --pkg-config-flags="--static" \
    --extra-ldflags="-static -lpthread" \
    --extra-cflags="-static"

RUN make -j$(nproc)
RUN make install DESTDIR=/ffmpeg-install

# ======================== Stage 2: frontend builder =========================
FROM node:22-alpine AS frontend-builder

WORKDIR /app

# 安装 npm 依赖
COPY web_frontend/package.json web_frontend/package-lock.json ./
RUN npm ci

# 复制源码并构建
COPY web_frontend/ ./
RUN npm run build --ignore-scripts

# ========================== Stage 3: app runtime ============================
FROM python:3.11-slim

LABEL org.opencontainers.image.title="seseget"
LABEL org.opencontainers.image.description="seseget 媒体资源下载工具 Web 面板"

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# 创建用户
RUN useradd --create-home --uid 1000 seseget

# 从 Stage 1 复制静态编译的 ffmpeg/ffprobe
COPY --from=ffmpeg-builder /ffmpeg-install/usr/local/bin/ffmpeg /usr/local/bin/
COPY --from=ffmpeg-builder /ffmpeg-install/usr/local/bin/ffprobe /usr/local/bin/

RUN ffmpeg -version && ffprobe -version

# 设置工作目录
WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt ./
COPY web_app/requirements.txt web_app-requirements.txt
RUN pip install --no-cache-dir \
    -r requirements.txt \
    -r web_app-requirements.txt

# 复制项目源码
COPY seseget/ ./seseget/
COPY web_app/ ./web_app/

# 从 Stage 2 复制前端构建产物
COPY --from=frontend-builder /app/dist/ ./web_app/static/

# 创建数据 & 配置目录
RUN mkdir -p /app/data /app/conf && chown -R seseget:seseget /app

USER seseget

EXPOSE 12450

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:12450')" || exit 1

CMD ["python", "-m", "web_app", "--prod", "--host", "0.0.0.0", "--port", "12450"]
