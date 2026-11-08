#!/bin/sh
# seseget 容器入口：按 PUID/PGID 创建/调整运行用户，设置 UMASK 后降权启动。
set -eu

PUID=${PUID:-1000}
PGID=${PGID:-1000}
UMASK=${UMASK:-022}

die() {
    printf 'seseget: ERROR: %s\n' "$*" >&2
    exit 1
}

warn() {
    printf 'seseget: WARNING: %s\n' "$*" >&2
}

is_uint() {
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

is_uint "$PUID" || die "PUID 必须是非负整数，当前值: '$PUID'"
is_uint "$PGID" || die "PGID 必须是非负整数，当前值: '$PGID'"
case "$UMASK" in
    [0-7][0-7][0-7]) ;;
    *) die "UMASK 必须是三位八进制（如 022），当前值: '$UMASK'" ;;
esac

[ "$#" -gt 0 ] || die "没有可执行的启动命令"

# compose 里指定 user: 或 docker run --user 时，没有权限创建用户，直接运行
if [ "$(id -u)" != "0" ]; then
    umask "$UMASK"
    exec "$@"
fi

command -v gosu >/dev/null 2>&1 || die "镜像缺少 gosu，无法降权运行"
command -v getent >/dev/null 2>&1 || die "镜像缺少 getent，无法创建运行用户"
command -v groupadd >/dev/null 2>&1 || die "镜像缺少 groupadd，无法创建运行用户"
command -v useradd >/dev/null 2>&1 || die "镜像缺少 useradd，无法创建运行用户"

umask "$UMASK"
export HOME=/home/seseget

# 运行时创建/对齐 seseget 组和用户，不依赖镜像构建阶段
if getent group seseget >/dev/null 2>&1; then
    CURRENT_GID=$(getent group seseget | cut -d: -f3)
    if [ "$CURRENT_GID" != "$PGID" ]; then
        groupmod -o -g "$PGID" seseget || die "把 seseget 组 ID 改为 $PGID 失败"
    fi
else
    groupadd -o -g "$PGID" seseget || die "创建 seseget 组失败（PGID=$PGID）"
fi

if id -u seseget >/dev/null 2>&1; then
    usermod -o -u "$PUID" -g seseget seseget || die "把 seseget 用户 ID 改为 $PUID 失败"
else
    useradd -o -u "$PUID" -g seseget -M -d /home/seseget -s /usr/sbin/nologin seseget \
        || die "创建 seseget 用户失败（PUID=$PUID）"
fi

# 镜像内可写目录；不 chown 宿主挂载目录
mkdir -p /home/seseget /app/web_app/static/files \
    || die "创建运行时目录失败"
chown -R "$PUID:$PGID" /home/seseget /app/web_app/static/files \
    || warn "无法修改 /home/seseget 或封面缓存目录属主，继续启动"

# data/conf 若不存在则创建；已存在的挂载目录保持原属主，只检查可写
for dir in /app/data /app/conf; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir" || die "创建目录失败: $dir"
        chown "$PUID:$PGID" "$dir" || die "设置目录属主失败: $dir"
    fi
    if ! gosu "$PUID:$PGID" test -w "$dir"; then
        die "$dir 对 $PUID:$PGID 不可写；请把 PUID/PGID 设为该目录的属主或有权限的用户"
    fi
done

exec gosu "$PUID:$PGID" "$@"
