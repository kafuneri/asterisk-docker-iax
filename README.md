# **注意：所有代码均为AI生成，不保证可用性，请根据您的个人硬件配置进行调整**

# Asterisk EC20 IAX2 Gateway

这是一个基于 Docker 的轻量级 Asterisk 融合通信网关方案。它专为 **EC20CEFAG-512-SGNS**设计，集成了 **IAX2 语音通话**与 **多渠道消息转发（Telegram / QQ / 钉钉）** 功能。

通过 Docker 容器化部署，实现了配置与环境的分离，只需简单修改 `docker-compose.yml` 即可快速搭建属于自己的移动通信网关。



## ✨ 主要功能

* **📞 语音通话**：通过 IAX2 协议对接软电话（如 Zoiper），实现远程接打手机电话。
* **📩 短信转发**：收到短信自动转发至 Telegram、QQ 和钉钉。
* **📡 来电通知**：来电/挂断事件实时推送到指定通知渠道。
* **🤖 Tg短信发送**：支持通过 Telegram 发送短信指令。
* **🔊 UAC 音频**：直接透传宿主机声卡，支持 EC20 的数字音频，音质清晰。

## 🛠️ 硬件与环境要求

1. **宿主机**：Linux 设备，7x24小时运行（如 Orange Pi, Raspberry Pi, x86 小主机等）。
2. **通信模块**：Quectel EC20/EC25 系列 4G 模块（USB 接口），推荐**EC20CEFAG-512-SGNS**，其他型号未作可行性验证
3. **软件环境**：Docker & Docker Compose。
4. **驱动要求**：宿主机需识别到 `/dev/ttyUSB*` 串口及 `/dev/snd/*` 声卡设备。

---

## ⚙️ 配置指南 (核心)

## 以下说明仅包含该项目配置，模块设置请参考以下博客

[**EC20 模块+Issabel 实现网络电话**](https://hanako.me/ec20_issabel.html)

[使用EC20模块配合asterisk及freepbx实现短信转发和网络电话](https://blog.sparktour.me/posts/2022/10/08/quectel-ec20-asterisk-freepbx-gsm-gateway/)

[**安装基于 Quectel EC20 模块的短信及语音转发服务**](https://blog.wsl.moe/2023/03/%E5%AE%89%E8%A3%85%E5%9F%BA%E4%BA%8E-quectel-ec20-%E6%A8%A1%E5%9D%97%E7%9A%84%E7%9F%AD%E4%BF%A1%E5%8F%8A%E8%AF%AD%E9%9F%B3%E8%BD%AC%E5%8F%91%E6%9C%8D%E5%8A%A1/)

[iPhone_air_esim_tutorial](https://github.com/AmorXxx/iPhone_air_esim_tutorial)



本项目的核心配置位于 `docker-compose.yml`。请根据您的实际环境修改以下参数。

### 1. 硬件设备映射 (Devices)

为了防止主机重启后 USB 端口号（如 `ttyUSB0`）发生漂移，**强烈建议使用 `by-id` 路径**。

请在宿主机执行 `ls -l /dev/serial/by-id/` 查看您的设备 ID，并替换下方配置：

```yaml
    devices:
      # ⚠️ 请根据您的 ls -l /dev/serial/by-id/ 结果修改冒号前的路径
      - /dev/serial/by-id/usb-Android_Android-if00-port0:/dev/ttyUSB0  # 对应诊断口
      - /dev/serial/by-id/usb-Android_Android-if01-port0:/dev/ttyUSB1  # 对应音频/GPS口 (重要)
      - /dev/serial/by-id/usb-Android_Android-if02-port0:/dev/ttyUSB2  # 对应AT指令口 (重要)
      - /dev/serial/by-id/usb-Android_Android-if03-port0:/dev/ttyUSB3  # 对应拨号口
      - /dev/snd:/dev/snd  # 必须挂载，用于 UAC 音频透传

```

### 2. 环境变量详解 (Environment)

所有业务逻辑开关和账号密码均在此处配置，**无需修改代码文件**。

#### 📢 通知渠道开关

通过 `1` (开启) 和 `0` (关闭) 来控制消息推送到哪些平台。顺序固定为：**Telegram, QQ, 钉钉**。

| 变量名               | 示例值  | 说明                                      |
| -------------------- | ------- | ----------------------------------------- |
| `SMS_NOTIFY_SWITCH`  | `1,1,1` | **短信通知**：同时推送到 TG、QQ 和钉钉。  |
| `CALL_NOTIFY_SWITCH` | `0,1,0` | **来电通知**：仅推送到 QQ，其他渠道屏蔽。 |

#### 🔐 IAX2 软电话认证

用于配置手机端 Zoiper 等客户端的连接信息。

| 变量名     | 示例值             | 说明                    |
| ---------- | ------------------ | ----------------------- |
| `IAX_USER` | `666`              | IAX2 用户名（分机号）。 |
| `IAX_PASS` | `your_secret_pass` | IAX2 连接密码。         |

#### 🤖 机器人凭证

**Telegram:**

| 变量名           | 说明                                     |
| :--------------- | :--------------------------------------- |
| `TG_TOKEN`       | BotFather 提供的 Token。                 |
| `TG_ALLOWED_IDS` | 允许控制 Bot 的用户 ID（防止他人滥用）。 |

**QQ (基于 OneBot/NapCat):**

**Api配置**详细说明参见：[onebot-11](https://github.com/botuniverse/onebot-11/blob/master/communication/http.md)

| 变量名            | 说明                                                         |
| :---------------- | :----------------------------------------------------------- |
| `QQ_API_URL`      | HTTP API 地址，例如 `http://192.168.1.5:3000/send_private_msg`。 |
| `QQ_BEARER_TOKEN` | 鉴权 Token (Access Token)。                                  |
| `QQ_USER_ID`      | 接收消息的 QQ 号。                                           |

**钉钉 (DingTalk):**

 **Api配置**详细说明参见：[钉钉开发者平台](https://open.dingtalk.com/document/dingstart/webhook-robot)

| 变量名      | 说明                                 |
| :---------- | :----------------------------------- |
| `DD_TOKEN`  | Webhook 地址中的 access_token 部分。 |
| `DD_SECRET` | 加签模式的 Secret 密钥。             |

#### 🛠️ 系统设置

| 变量名                   | 说明                                                         |
| ------------------------ | ------------------------------------------------------------ |
| `MY_PHONE_NUMBER`        | 本机号码，用于日志显示。                                     |
| `STARTUP_SILENCE_WINDOW` | **启动静默期 (秒)**。设为 `10` 表示启动后 10 秒内读取到的旧短信/日志会被丢弃，防止重启刷屏。 |
| `PROXY_URL`              | Telegram 代理地址（如 `http://192.168.1.2:7890`），国内环境通常需要。不使用填 `None`。 |

---

## 🚀 部署与启动

### 1. 目录结构

执行`https://github.com/kafuneri/asterisk-docker-iax.git && cd asterisk-docker-iax.git`

确保您的项目目录包含以下文件：

```text
.
├── config/              # 配置文件目录 (extensions.conf, iax.conf 等)
├── logs/                # 日志挂载目录
├── bot.py               # Python 机器人脚本
├── start.sh             # 启动入口脚本
├── Dockerfile           # 镜像构建文件
└── docker-compose.yml   # 核心配置文件

```

### 2. 构建并启动

> 默认使用已构建镜像，您可以选择自行构建
>
> 修改`docker-compose.yml`，去除`build`部分的注释，保存后执行`docker compose up -d--build`

在项目根目录下执行：

```bash
# 后台启动
docker compose up -d

```

### 3. 查看运行状态

```bash
# 查看实时日志
docker compose logs -f

```

如果看到 `Bot 已启动` 和 `Asterisk Ready` 字样，说明服务正常。

---

## 📱 客户端连接指南 (Zoiper)

推荐使用 **Zoiper** (iOS/Android/PC) 进行连接。

1. **新建账户**：选择手动配置。
2. **账户类型**：选择 **IAX** (不是 SIP)。
3. **Host (主机)**：`宿主机IP:23388` (注意端口是 docker-compose 中映射的外部端口)。
4. **Username (用户名)**：对应环境变量 `IAX_USER` (如 888666)。
5. **Password (密码)**：对应环境变量 `IAX_PASS`。
6. **Caller ID**：随意填写。
7. **高级设置**：无需特殊设置，默认即可。

连接成功后，状态栏应显示 "Registered" 或 "OK"。

---

## ❓ 常见问题

**Q: 系统运行正常，但突然收不到新短信了？**

这通常是因为 SIM 卡的硬件存储空间已满（通常上限为 50 条）。一旦存满，运营商的新短信将被阻塞。建议定期执行清空指令。

1. 手动诊断与修复

在宿主机执行以下命令：

```bash
# 1. 查询当前存储状态 假设容器名称为asterisk-ec20
# 预期回复示例: +CPMS: "SM",50,50... (前面的 50 表示已用，后面的 50 表示总容量)
docker exec asterisk-ec20 asterisk -rx "quectel cmd quectel0 AT+CPMS?"

# 2. 强制清空 SIM 卡 (解决问题)
# AT+CMGD=1,4 表示删除所有类型的短信
docker exec asterisk-ec20 asterisk -rx "quectel cmd quectel0 AT+CMGD=1,4"
```

2. 设置自动清理 (推荐)

建议在宿主机设置 crontab 计划任务，每天凌晨自动清理一次，确保持久稳定。

- **编辑计划任务**: `crontab -e`
- **添加如下一行** (每天凌晨 4:30 执行清理):

```Bash
30 4 * * * docker exec asterisk-ec20 asterisk -rx "quectel cmd quectel0 AT+CMGD=1,4"
```

> **提示**: 如果您使用 1Panel 或宝塔面板，可以直接在“计划任务”中添加上述 Shell 脚本命令。

**Q: 启动时提示 `Unable to open /dev/ttyUSB*`？**  

请检查 `docker-compose.yml` 中的 `devices` 映射路径是否正确，以及宿主机是否已插上 4G 模块。

**Q: Zoiper 注册成功但没有声音？**

1. 检查 `docker-compose.yml` 是否开启了 `privileged: true`。
2. 检查 `/dev/snd` 是否正确挂载。
3. 确保宿主机上没有其他程序（如 PulseAudio）独占声卡。
---


**Q: 重启容器后收到一堆旧短信通知？**  

适当调大 `STARTUP_SILENCE_WINDOW` 的值（例如 20 或 40），让 Bot 在启动初期自动清理积压的旧日志。
