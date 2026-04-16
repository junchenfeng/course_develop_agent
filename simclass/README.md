# SimClass — AI 模拟学生备课练习系统

CLI 驱动的本地备课练习工具：新手教师通过语音与 AI 模拟学生互动，练习授课技能，课后获得自动化教学反馈。

## 快速开始

### 1. 安装

```bash
cd simclass
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，至少填写 OPENROUTER_API_KEY
```

### 3. 验证教案

```bash
simclass validate examples/python_variables.yaml
```

### 4. 启动练课

```bash
# 完整模式（需要 STT 配置 + 麦克风 + 屏幕录制）
simclass start examples/python_variables.yaml

# 文字输入模式（不配置 STT 时自动降级，不需要麦克风）
simclass start examples/python_variables.yaml --no-screen

# 指定 STT 和 LLM
simclass start examples/python_variables.yaml --stt deepgram --llm openai/gpt-4o-mini
```

### 5. 分析练课

```bash
simclass analyze sessions/sess_20260416_143022
```

### 6. 查看报告

```bash
simclass report sessions/sess_20260416_143022
```

### 7. 其他命令

```bash
simclass sessions        # 列出历史会话
simclass replay <path>   # 文字回放
simclass version         # 版本号
```

## 项目结构

```
simclass/
├── pyproject.toml              # 项目元数据和依赖
├── .env.example                # 环境变量模板
├── README.md
│
├── simclass/                   # 源代码
│   ├── __init__.py
│   ├── cli.py                  # CLI 入口 (typer)
│   ├── config.py               # 配置加载
│   │
│   ├── models/                 # 数据模型
│   │   ├── lesson.py           # 教案（YAML 解析）
│   │   └── session.py          # 会话 + 时间线
│   │
│   ├── agents/                 # AI 学生 Agent
│   │   ├── student_agent.py    # Agent 决策逻辑
│   │   ├── prompts.py          # System Prompt 模板
│   │   └── llm_client.py       # OpenRouter LLM 调用
│   │
│   ├── services/               # 核心服务
│   │   ├── orchestrator.py     # 会话编排器
│   │   ├── recorder.py         # 音频 + 屏幕录制
│   │   ├── analyzer.py         # 教学分析器
│   │   └── stt/                # 语音识别
│   │       ├── base.py         # STT 抽象接口
│   │       ├── seedasr.py      # 火山引擎 SeedASR
│   │       └── deepgram.py     # Deepgram（fallback）
│   │
│   └── ui/
│       └── terminal.py         # 终端 UI (rich)
│
├── examples/
│   └── python_variables.yaml   # 示例教案
│
├── tests/
│   ├── unit/
│   │   ├── test_lesson_model.py
│   │   └── test_config.py
│   └── integration/
│
└── sessions/                   # 会话数据（gitignored）
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENROUTER_API_KEY` | 是 | OpenRouter API Key |
| `SIMCLASS_AGENT_MODEL` | 否 | Agent 用的 LLM 模型（默认 `openai/gpt-4o-mini`） |
| `SIMCLASS_ANALYZER_MODEL` | 否 | 分析器用的 LLM 模型（默认 `openai/gpt-4o`） |
| `SIMCLASS_STT_PROVIDER` | 否 | STT 提供商：`seedasr`（默认）或 `deepgram` |
| `SEED_ASR_APP_ID` | 条件 | 火山引擎 AppID（选 seedasr 时必填） |
| `SEED_ASR_TOKEN` | 条件 | 火山引擎 Token（选 seedasr 时必填） |
| `DEEPGRAM_API_KEY` | 条件 | Deepgram API Key（选 deepgram 时必填） |
| `FFMPEG_PATH` | 否 | ffmpeg 路径（默认 `ffmpeg`，屏幕录制编码用） |
| `SIMCLASS_SESSIONS_DIR` | 否 | 会话存储目录（默认 `./sessions`） |

## 技术栈

- **CLI**: typer + rich
- **LLM**: OpenRouter（openai SDK 兼容）
- **STT**: 火山引擎 SeedASR / Deepgram Nova-3
- **音频**: sounddevice + soundfile
- **屏幕录制**: mss + pillow + ffmpeg
- **数据**: pydantic + pyyaml
