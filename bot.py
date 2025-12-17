import os
import time
import logging
import subprocess
import json
import urllib.request
import urllib.parse
import hmac
import hashlib
import base64
import re
from datetime import datetime
from telegram.ext import Updater, CommandHandler
from telegram import Update
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= 配置区域 (从环境变量读取) =================

# 1. Telegram
TG_TOKEN = os.getenv("TG_TOKEN", "")
_ids_str = os.getenv("TG_ALLOWED_IDS", "")
ALLOWED_IDS = []
try:
    if _ids_str:
        ALLOWED_IDS = [int(x.strip()) for x in _ids_str.split(',') if x.strip()]
except Exception:
    pass

# 2. QQ 机器人
QQ_API = os.getenv("QQ_API_URL", "")
QQ_BEARER = os.getenv("QQ_BEARER_TOKEN", "")
try:
    QQ_USER_ID = int(os.getenv("QQ_USER_ID", "0"))
except ValueError:
    QQ_USER_ID = 0

# 3. 钉钉机器人
DD_TOKEN = os.getenv("DD_TOKEN", "")
DD_SECRET = os.getenv("DD_SECRET", "")

# 4. 其他配置
MESSAGE_DIR = "/var/log/asterisk/unread_sms/"
MY_NUM = os.getenv("MY_PHONE_NUMBER", "Unknown")

# 启动静默期
try:
    STARTUP_SILENCE_WINDOW = int(os.getenv("STARTUP_SILENCE_WINDOW", "40"))
except ValueError:
    STARTUP_SILENCE_WINDOW = 40

# 代理配置
_proxy_url = os.getenv("PROXY_URL", "").strip()
if _proxy_url and _proxy_url.lower() != "none":
    PROXY = {'proxy_url': _proxy_url}
else:
    PROXY = None

# === 【核心】通知开关解析逻辑 ===
def parse_switch_config(env_var_name, default_str):
    """
    解析 '1,0,1' 格式的字符串
    返回: [TG_Enabled, QQ_Enabled, DD_Enabled] (Bool List)
    """
    raw = os.getenv(env_var_name, default_str)
    switches = [False, False, False] # 默认全关，防止异常
    try:
        parts = raw.split(',')
        # 取前3位，对应 TG, QQ, DD
        for i in range(min(len(parts), 3)):
            if parts[i].strip() == '1':
                switches[i] = True
    except Exception as e:
        print(f"Error parsing {env_var_name}: {e}")
        return [True, True, True] # 解析失败则默认全开，防止漏消息
    return switches

# 读取开关 (TG, QQ, DD)
SMS_SWITCHES = parse_switch_config("SMS_NOTIFY_SWITCH", "1,1,1")
CALL_SWITCHES = parse_switch_config("CALL_NOTIFY_SWITCH", "0,1,0")

# 记录 Bot 启动时间
BOT_START_TIMESTAMP = time.time()

# ================= 日志设置 =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================= 核心：解析逻辑 =================

def parse_sms_content(raw_content):
    """解析短信"""
    try:
        text = raw_content.strip()
        pattern = r"From:\s*(.*?)\s*Content:\s*(.*)"
        match = re.search(pattern, text, re.S | re.I)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return "未知号码", text
    except Exception:
        return "解析错误", raw_content

def parse_call_content(raw_content):
    """解析来电/挂断"""
    data = {}
    try:
        if '|' in raw_content:
            parts = raw_content.strip().split('|')
        else:
            parts = raw_content.strip().split('\n')

        for part in parts:
            if ':' in part:
                key, val = part.split(':', 1)
                data[key.strip()] = val.strip()
        
        call_type = data.get('TYPE', 'UNKNOWN')
        number = data.get('NUM', '未知')
        call_time = data.get('TIME', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return call_type, number, call_time
    except Exception as e:
        logger.error(f"来电解析失败: {e}")
        return None, None, None

# ================= 发送通道 =================

def send_http_request(url, data, headers=None):
    try:
        if not url: return
        if not headers: headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response: return
    except Exception as e: logger.error(f"HTTP Err: {e}")

def send_qq(text):
    if not QQ_API: return
    headers = {"Authorization": f"Bearer {QQ_BEARER}", "Content-Type": "application/json"}
    send_http_request(QQ_API, {"user_id": QQ_USER_ID, "message": text}, headers)

def send_dingtalk(text):
    if not DD_TOKEN: return
    try:
        timestamp = str(round(time.time() * 1000))
        secret_enc = DD_SECRET.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, DD_SECRET)
        hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"https://oapi.dingtalk.com/robot/send?access_token={DD_TOKEN}&timestamp={timestamp}&sign={sign}"
        send_http_request(url, {"msgtype": "text", "text": {"content": text}})
    except Exception as e:
        logger.error(f"DingTalk Config Err: {e}")

def send_telegram(bot, chat_ids, text):
    if not TG_TOKEN: return
    for cid in chat_ids:
        try: bot.send_message(chat_id=cid, text=text)
        except Exception as e: logger.error(f"TG Err: {e}")

# === 【核心】统一分发函数 ===
def dispatch_message(bot, allowed_ids, text, switches):
    """
    根据 switches 开关决定发送给谁
    switches: [TG_Enabled, QQ_Enabled, DD_Enabled]
    """
    msg_preview = text.splitlines()[0]
    
    # 1. Telegram
    if switches[0]:
        send_telegram(bot, allowed_ids, text)
        
    # 2. QQ
    if switches[1]:
        send_qq(text)
        
    # 3. DingTalk
    if switches[2]:
        send_dingtalk(text)
    
    # 日志记录 (显示实际发送了哪些渠道)
    channels = []
    if switches[0]: channels.append("TG")
    if switches[1]: channels.append("QQ")
    if switches[2]: channels.append("DingTalk")
    logger.info(f"消息已分发至 {channels}: {msg_preview}...")

# ================= 文件监控 =================

def read_and_remove(path):
    if not os.path.exists(path): return None
    time.sleep(0.2)
    try:
        with open(path, 'r', encoding='utf-8') as f: content = f.read().strip()
        os.remove(path)
        return content
    except Exception: return None

class SMSFileHandler(FileSystemEventHandler):
    def __init__(self, bot, allowed_ids):
        self.bot = bot
        self.allowed_ids = allowed_ids

    def on_created(self, event):
        if event.is_directory: return
        filename = event.src_path
        
        if not (filename.endswith('.txt') or filename.endswith('.req')): return

        # 启动静默期检查
        uptime = time.time() - BOT_START_TIMESTAMP
        if uptime < STARTUP_SILENCE_WINDOW:
            logger.warning(f"🔇 [静默期 {int(uptime)}s/{STARTUP_SILENCE_WINDOW}s] 丢弃: {os.path.basename(filename)}")
            try: os.remove(filename)
            except: pass
            return

        raw_content = read_and_remove(filename)
        if not raw_content: return

        # --- 短信处理 (.txt) ---
        if filename.endswith('.txt'):
            sender, content = parse_sms_content(raw_content)
            final_msg = (
                f"{content}\n\n"
                f"发件号码: {sender}\n"
                f"发件时间: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n"
                f"本机号码: {MY_NUM}"
            )
            logger.info(f"收到短信: {sender}")
            # 使用 SMS_SWITCHES 开关
            dispatch_message(self.bot, self.allowed_ids, final_msg, SMS_SWITCHES)

        # --- 来电处理 (.req) ---
        elif filename.endswith('.req'):
            call_type, number, time_str = parse_call_content(raw_content)
            if not call_type: return

            call_msg = ""
            if call_type == 'IN':
                call_msg = (
                    f"📞来电通知\n\n"
                    f"来电号码: {number}\n"
                    f"来电时间: {time_str}\n"
                    f"#CALL #CALL_IN\n"
                    f"本机号码: {MY_NUM}"
                )
            elif call_type == 'UP':
                call_msg = (
                    f"📴 来电挂断\n\n"
                    f"来电号码: {number}\n"
                    f"挂断时间: {time_str}\n"
                    f"#CALL #CALL_DISCONNECTED\n"
                    f"本机号码: {MY_NUM}"
                )
            
            logger.info(f"通话事件 ({call_type})")
            # 使用 CALL_SWITCHES 开关
            dispatch_message(self.bot, self.allowed_ids, call_msg, CALL_SWITCHES)

# ================= 交互命令 =================
def get_user_id(update: Update, context):
    update.message.reply_text(f"ID: {update.message.from_user.id}")

def send_sms_cmd(update: Update, context):
    if update.message.from_user.id not in ALLOWED_IDS: return
    if len(context.args) < 2:
        update.message.reply_text("用法: /send <号码> <内容>")
        return
    phone = context.args[0]
    msg = " ".join(context.args[1:])
    cmd = ["asterisk", "-rx", f'quectel sms quectel0 {phone} "{msg}"']
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and "error" not in res.stdout.lower():
            update.message.reply_text(f"✅ 已发送给 {phone}")
        else:
            update.message.reply_text(f"❌ 失败: {res.stdout}")
    except Exception as e:
        update.message.reply_text(f"❌ 异常: {e}")

# ================= 主程序 =================
def cleanup_old_files():
    if not os.path.exists(MESSAGE_DIR):
        os.makedirs(MESSAGE_DIR)
        return
    for filename in os.listdir(MESSAGE_DIR):
        file_path = os.path.join(MESSAGE_DIR, filename)
        try:
            if os.path.isfile(file_path): 
                os.unlink(file_path)
        except: pass

def main():
    cleanup_old_files()
    
    if not TG_TOKEN:
        logger.error("❌ 未检测到 TG_TOKEN (或不需要TG)，但Bot正在启动...")

    updater = Updater(TG_TOKEN, use_context=True, request_kwargs=PROXY)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("myid", get_user_id))
    dp.add_handler(CommandHandler("send", send_sms_cmd))

    observer = Observer()
    observer.schedule(SMSFileHandler(updater.bot, ALLOWED_IDS), MESSAGE_DIR, recursive=False)
    observer.start()

    logger.info(f"Bot 已启动 | 静默期: {STARTUP_SILENCE_WINDOW}s")
    logger.info(f"短信通知开关 [TG,QQ,DD]: {SMS_SWITCHES}")
    logger.info(f"来电通知开关 [TG,QQ,DD]: {CALL_SWITCHES}")
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()