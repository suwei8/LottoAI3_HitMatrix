# Dockerfile
FROM python:3.11-slim

ENV TZ=Asia/Shanghai

RUN apt-get update && apt-get install -y \
    unzip curl zip gnupg2 pv mysql-client git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 注意：这里不 COPY 项目文件

# 安装 Python requirements（交由 docker-compose run 时执行）
CMD ["bash"]
