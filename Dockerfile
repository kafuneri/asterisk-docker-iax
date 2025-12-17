# Base Image: Python 3.10 Slim (Debian Bullseye)
# 基础镜像：使用基于 Debian 11 的 Python 3.10 精简版
FROM python:3.10-slim-bullseye

# Optimization: Switch to local mirrors for faster build
# 优化：替换为国内 USTC 镜像源以加速构建过程
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list \
    && sed -i 's|security.debian.org/debian-security|mirrors.ustc.edu.cn/debian-security|g' /etc/apt/sources.list

# Install Dependencies for Asterisk and Compilation
# 安装 Asterisk 主程序及编译驱动所需的依赖库
RUN apt-get update && apt-get install -y \
    asterisk \
    asterisk-dev \
    build-essential \
    git \
    autoconf \
    automake \
    libtool \
    pkg-config \
    libsqlite3-dev \
    libasound2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Compile and Install chan_quectel driver
# 下载并编译 Quectel EC20 驱动模块
WORKDIR /usr/src
RUN git clone https://github.com/IchthysMaranatha/asterisk-chan-quectel.git \
    && cd asterisk-chan-quectel \
    && ./bootstrap \
    && ./configure --with-astversion=16 --with-asterisk=/usr/include \
    && make \
    && make install \
    && cp uac/quectel.conf /etc/asterisk/

# Install Python Bot Dependencies
# 安装 Python 机器人所需的第三方库
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
    python-telegram-bot==13.7 \
    watchdog

# Setup Runtime Directories and Permissions
# 配置运行时目录及权限
RUN mkdir -p /var/log/asterisk/unread_sms && chmod 777 /var/log/asterisk/unread_sms

# Setup Startup Script
# 设置启动脚本权限
# RUN chmod +x /opt/start.sh

# Cleanup: Remove build tools to reduce image size
# 清理：移除编译工具以减小镜像体积 (保留运行时必要的库)
RUN apt-get purge -y build-essential git asterisk-dev \
    && apt-get autoremove -y \
    && apt-get clean

# Entrypoint
# 启动入口
CMD ["/opt/start.sh"]