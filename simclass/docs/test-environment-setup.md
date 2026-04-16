# SimClass 测试环境搭建指南（虚拟机）

本文档说明如何在一台虚拟机上搭建 SimClass 的完整测试环境。

---

## 1. 虚拟机基础要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Ubuntu 22.04+ / macOS 13+ / Windows 10+ |
| **Python** | 3.11 或更高 |
| **内存** | 最低 2GB（推荐 4GB） |
| **磁盘** | 最低 5GB 可用空间（录制视频会占用空间） |
| **网络** | 需要外网访问（调用 OpenRouter API 和 STT 服务） |
| **音频设备** | 需要麦克风（虚拟机需透传宿主机麦克风，或使用虚拟音频设备） |
| **显示** | 需要图形桌面环境（屏幕录制需要）；纯 CLI 模式可用 `--no-screen` 跳过 |

---

## 2. 系统级依赖安装

### Ubuntu / Debian

```bash
# 基础工具
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git

# 音频支持（sounddevice 依赖 PortAudio）
sudo apt install -y portaudio19-dev

# 屏幕录制（ffmpeg 用于截屏序列编码为 MP4）
sudo apt install -y ffmpeg

# 如果虚拟机没有图形环境但需要屏幕录制，安装虚拟帧缓冲
# sudo apt install -y xvfb
# Xvfb :99 -screen 0 1920x1080x24 &
# export DISPLAY=:99
```

### macOS

```bash
brew install python@3.11 portaudio ffmpeg
```

### Windows

```powershell
# 1. 安装 Python 3.11+ (https://python.org)
# 2. 安装 ffmpeg (https://ffmpeg.org/download.html)，加入 PATH
# 3. PortAudio 会由 sounddevice 自动安装
```

---

## 3. 项目安装

```bash
git clone <repo-url>
cd simclass

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 安装项目（含开发依赖）
pip install -e ".[dev]"

# 验证安装
simclass version
```

---

## 4. 配置 API Keys

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置：

```bash
# 必填 — OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# STT 选一个配置：

# 选项 A: 火山引擎 SeedASR（需要申请火山引擎账号）
SIMCLASS_STT_PROVIDER=seedasr
SEED_ASR_APP_ID=your_app_id
SEED_ASR_TOKEN=your_token

# 选项 B: Deepgram（注册即有 $200 免费额度）
SIMCLASS_STT_PROVIDER=deepgram
DEEPGRAM_API_KEY=your_deepgram_key
```

加载环境变量：

```bash
# 方式 1: source
set -a && source .env && set +a

# 方式 2: 使用 direnv（推荐）
# sudo apt install direnv
# echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
# direnv allow
```

---

## 5. 虚拟机特殊配置

### 5.1 麦克风透传

**VirtualBox**:
- 设置 → 音频 → 启用音频输入

**VMware**:
- 虚拟机设置 → 声卡 → 勾选"在录制时连接"

**云虚拟机（无物理麦克风）**:
- 使用文字输入模式：`simclass start lesson.yaml --no-screen`
- 或安装虚拟音频设备：
  ```bash
  # PulseAudio 虚拟输入（用于测试）
  sudo apt install -y pulseaudio
  pactl load-module module-null-sink sink_name=virtual_mic
  pactl set-default-source virtual_mic.monitor
  ```

### 5.2 无图形环境（Headless）

如果虚拟机没有桌面环境，屏幕录制不可用。使用 `--no-screen` 跳过：

```bash
simclass start examples/python_variables.yaml --no-screen
```

如需在 headless 环境测试屏幕录制功能：

```bash
sudo apt install -y xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### 5.3 检查音频设备

```bash
# 列出可用的音频输入设备
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

---

## 6. 运行测试

```bash
# 单元测试
pytest tests/unit/ -v

# 带覆盖率
pytest tests/unit/ -v --cov=simclass --cov-report=term-missing

# Lint
ruff check simclass/
ruff format --check simclass/
```

---

## 7. 功能验证清单

按以下顺序验证各功能模块：

### 7.1 教案解析

```bash
simclass validate examples/python_variables.yaml
# 预期：显示教案信息表格，验证通过
```

### 7.2 文字输入模式（不需要 STT 和麦克风）

```bash
# 不配置任何 STT key，系统自动降级为文字输入模式
simclass start examples/python_variables.yaml --no-screen
# 预期：进入文字输入模式，输入教师讲话内容后 AI 学生文字回复
```

### 7.3 STT + 语音模式

```bash
# 配置好 STT key 后
simclass start examples/python_variables.yaml
# 预期：麦克风采集语音 → 实时转写 → AI 学生回复
```

### 7.4 课后分析

```bash
simclass sessions
simclass analyze sessions/<session_id>
simclass report sessions/<session_id>
# 预期：生成 Markdown 分析报告
```

### 7.5 回放

```bash
simclass replay sessions/<session_id> --speed 5
# 预期：按时间线回放课堂内容
```

---

## 8. 常见问题

| 问题 | 解决方案 |
|------|----------|
| `No module named sounddevice` | `sudo apt install portaudio19-dev && pip install sounddevice` |
| `ALSA lib ... Unknown PCM` | 正常（Linux ALSA 警告），不影响功能 |
| ffmpeg not found | `sudo apt install ffmpeg` 或设置 `FFMPEG_PATH` |
| 麦克风无输入 | 检查 `python3 -c "import sounddevice; print(sounddevice.query_devices())"` |
| OpenRouter API 超时 | 检查网络；尝试更换模型 `--llm openai/gpt-4o-mini` |
| SeedASR 连接失败 | 检查 AppID/Token；尝试切换到 Deepgram `--stt deepgram` |
