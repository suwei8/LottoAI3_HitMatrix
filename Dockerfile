# 使用官方 Python 3.11 slim 镜像
FROM python:3.11-slim

# 安装系统依赖 + 官方 MySQL 8.0 客户端 + gh CLI
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gnupg \
    zip \
    gcc \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    wget \
    lsb-release \
    && wget https://dev.mysql.com/get/mysql-apt-config_0.8.29-1_all.deb \
    && echo "mysql-apt-config mysql-apt-config/select-server select mysql-8.0" | debconf-set-selections \
    && DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.29-1_all.deb \
    && apt-get update && apt-get install -y mysql-client \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*


# 升级 pip
RUN pip install --upgrade pip

# 设置工作目录
WORKDIR /app

# 复制 requirements 并安装依赖
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 拷贝项目代码
COPY . .

# 拷贝并启用 entrypoint 脚本（自动写入 ~/.config/gh/hosts.yml）
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 设置环境变量默认值（可被 docker-compose 覆盖）
ENV GH_USER=suwei8

# 启动 entrypoint 初始化 gh，然后保持容器运行
ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
