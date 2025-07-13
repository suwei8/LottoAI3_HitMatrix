#!/bin/bash
set -e

# 从 .env 读取 GH_TOKEN 和 GH_USER 并配置 GitHub CLI
if [ -n "$GH_TOKEN" ]; then
  mkdir -p /root/.config/gh
  cat > /root/.config/gh/hosts.yml <<EOF
github.com:
    oauth_token: $GH_TOKEN
    git_protocol: https
    user: ${GH_USER:-suwei8}   # 使用 .env 中的 GH_USER，默认为 suwei8
EOF
  echo "✅ GitHub CLI 配置已写入 ~/.config/gh/hosts.yml"
else
  echo "⚠️ GH_TOKEN 未设置，gh 命令将无法使用"
fi

# 执行传入的命令（继续启动容器）
exec "$@"
