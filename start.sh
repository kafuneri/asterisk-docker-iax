#!/bin/bash

# 1. Initialize Environment
# 1. 初始化环境
echo "Initializing Asterisk Container..."

# 2. Template Injection Logic
# 2. 配置模板注入逻辑
if [ -d "/etc/asterisk_templates" ]; then
    echo "Applying configuration templates..."

    # Copy templates to actual config directory
    # 将只读模板复制到可写的配置目录
    cp -r /etc/asterisk_templates/* /etc/asterisk/

    # Core: Inject Environment Variables using sed
    # 核心：使用 sed 将占位符替换为环境变量中的真实值
    USER=${IAX_USER:-888666}
    PASS=${IAX_PASS:-password}

    # Inject iax.conf
    # 替换 iax.conf
    sed -i "s/__IAX_USER__/$USER/g" /etc/asterisk/iax.conf
    sed -i "s/__IAX_PASS__/$PASS/g" /etc/asterisk/iax.conf

    # Inject extensions.conf
    # 替换 extensions.conf
    sed -i "s/__IAX_USER__/$USER/g" /etc/asterisk/extensions.conf

    echo "Configuration generated with User: $USER"
else
    echo "No templates found, using existing config."
fi

# 3. Start Python Bot (Background)
# 3. 启动 Python 机器人 (后台运行)
if [ -f "/opt/bot.py" ]; then
    echo "Starting Python Bot..."
    python3 /opt/bot.py &
fi

# 4. Start Asterisk (Foreground)
# 4. 启动 Asterisk 主程序 (前台运行)
echo "Starting Asterisk..."
exec asterisk -f