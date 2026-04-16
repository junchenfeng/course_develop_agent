# AI 模拟学生备课系统 — MVP 技术路线图

> 版本: v0.1 · 2026-04-16

---

## 1. 系统愿景

帮助教师在 ClassIn 桌面端上课时，右侧面板展示若干 **AI 模拟学生**；这些学生能根据教案、教师语音和屏幕演示进行提问与互动。课后系统录制教师行为并生成教学反馈分析报告。

### 1.1 核心用户故事

```
作为一名教师，我希望：
1. 上传我的教案/上课脚本，配置若干虚拟学生角色
2. 在 ClassIn 上开始一节模拟课
3. 右侧面板中的 AI 学生根据我的教学内容实时提问/回答
4. 我能通过语音与这些 AI 学生交流
5. 课后获得一份关于我教学表现的分析报告
```

### 1.2 系统约束

| 约束 | 说明 |
|------|------|
| 教师端 | ClassIn 桌面客户端（Windows/macOS），配合浏览器侧面板 |
| 学生端 | AI 模拟，无需真人参与 |
| 交互模式 | 教师 ↔ AI 学生（一对多）；学生之间不交互 |
| 延迟要求 | 语音交互端到端延迟 < 3 秒（MVP 可放宽到 5 秒） |

---

## 2. 整体架构

```
┌────────────────────────────────────────────────────────────┐
│                     教师工作站 (PC)                         │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │  ClassIn 桌面  │  │  浏览器侧面板（Student Panel Web） │  │
│  │  客户端       │  │  ┌──────┐ ┌──────┐ ┌──────┐      │  │
│  │              │  │  │学生 A│ │学生 B│ │学生 C│      │  │
│  │  (教师上课)   │  │  └──┬───┘ └──┬───┘ └──┬───┘      │  │
│  └──────────────┘  └─────┼────────┼────────┼───────────┘  │
│                          │ WebSocket / WebRTC              │
└──────────────────────────┼────────┼────────┼──────────────┘
                           ▼        ▼        ▼
              ┌────────────────────────────────────┐
              │       Backend Orchestrator          │
              │  ┌──────────┐  ┌────────────────┐  │
              │  │ Session   │  │ Audio Pipeline │  │
              │  │ Manager   │  │ (STT → LLM    │  │
              │  │           │  │  → TTS)        │  │
              │  └──────────┘  └────────────────┘  │
              │  ┌──────────┐  ┌────────────────┐  │
              │  │ Student   │  │ Lesson Context │  │
              │  │ Agent Pool│  │ Manager        │  │
              │  └──────────┘  └────────────────┘  │
              └────────────────┬───────────────────┘
                               │
              ┌────────────────┼───────────────────┐
              │         Post-Session Layer          │
              │  ┌──────────┐  ┌────────────────┐  │
              │  │ Session   │  │ Teaching       │  │
              │  │ Recorder  │  │ Analyzer       │  │
              │  └──────────┘  └────────────────┘  │
              └────────────────────────────────────┘
```

---

## 3. 技术方案选型

### 3.1 两种集成路径对比

#### 路径 A：ClassIn PaaS API + 外部 AI 面板（推荐 MVP）

| 组件 | 方案 |
|------|------|
| 教师上课 | ClassIn 桌面客户端正常上课 |
| AI 学生面板 | **独立 Web 应用**，教师在第二个屏幕或浏览器侧窗口打开 |
| ClassIn 集成 | 通过 ClassIn API 创建课程/课节，注册虚拟学生账号加入课堂 |
| 教师音频捕获 | 浏览器 Web Audio API 捕获系统音频 / 麦克风 |

**优点**：不依赖 ClassIn SDK 深度集成，开发速度快  
**缺点**：教师需要同时看 ClassIn 和浏览器面板，体验有割裂感

#### 路径 B：ClassIn SDK 深度嵌入

| 组件 | 方案 |
|------|------|
| 教师上课 | ClassIn SDK 嵌入到自研应用中 |
| AI 学生面板 | 与 ClassIn 教室在同一应用窗口 |
| 音频 | SDK 内部音频流直接接入 |

**优点**：体验统一  
**缺点**：SDK 接入周期长，需要商务合作，不适合 MVP

#### MVP 决策：采用路径 A

> 路径 A 可在不依赖 ClassIn SDK 的情况下快速验证核心价值。
> ClassIn 仅作为教师授课的"舞台"，AI 学生互动在独立 Web 面板中完成。
> 未来可升级为路径 B 实现一体化体验。

### 3.2 核心技术栈

| 层级 | 技术选择 | 说明 |
|------|----------|------|
| **前端** | React + TypeScript + Vite | AI 学生面板 Web 应用 |
| **实时通信** | WebSocket (Socket.IO) | 前后端双向通信 |
| **语音输入** | Web Audio API → WebSocket 流式传输 | 捕获教师麦克风音频 |
| **STT** | OpenAI Whisper API / Deepgram | 语音转文字 |
| **LLM** | OpenAI GPT-4o / Claude | 学生角色扮演 + 对话生成 |
| **TTS** | OpenAI TTS / ElevenLabs | 文字转语音（给每个学生不同声线） |
| **实时语音（进阶）** | OpenAI Realtime API (gpt-realtime) | 端到端语音对话，省去 STT/TTS 链路 |
| **后端** | Python (FastAPI) + Redis | 会话管理、Agent 编排 |
| **数据库** | PostgreSQL | 教案、学生配置、会话记录 |
| **对象存储** | S3 / MinIO | 音频录制文件存储 |
| **ClassIn 集成** | ClassIn PaaS API (Python SDK) | 创建课程、添加虚拟学生 |

---

## 4. 核心模块详细设计

### 4.1 模块一：教案与学生配置（Lesson Setup）

**功能**：教师上传教案脚本，配置模拟学生角色。

```yaml
# 教案配置示例
lesson:
  title: "Python 变量与数据类型"
  duration_minutes: 45
  script: |
    1. 开场（5分钟）：复习上节课内容
    2. 新课导入（10分钟）：什么是变量
    3. 演示（15分钟）：在 IDE 中演示变量赋值
    4. 练习（10分钟）：学生动手
    5. 总结（5分钟）

  key_concepts:
    - 变量定义与赋值
    - 数据类型：int, float, str, bool
    - type() 函数

students:
  - name: "小明"
    persona: "积极主动型"
    traits: "经常举手提问，理解力强，喜欢追问底层原理"
    knowledge_level: "中等偏上"
    
  - name: "小红"
    persona: "害羞安静型"
    traits: "很少主动发言，但被点名时能给出正确答案"
    knowledge_level: "中等"
    
  - name: "小刚"
    persona: "容易走神型"
    traits: "注意力不集中，经常问已经讲过的问题"
    knowledge_level: "中等偏下"
```

**技术实现**：
- Web 表单 + YAML/JSON 编辑器
- 预设学生角色模板库（MVP 提供 5-8 种典型学生人设）
- 教案解析为结构化的 `LessonContext` 对象

### 4.2 模块二：AI 学生 Agent（Student Agent）

**核心**：每个模拟学生是一个独立的 LLM Agent，拥有自己的人设、记忆和行为逻辑。

#### Agent 架构

```
┌─────────────────────────────────────┐
│          Student Agent              │
│  ┌───────────┐  ┌───────────────┐  │
│  │  Persona   │  │  Lesson       │  │
│  │  Profile   │  │  Context      │  │
│  │ (性格/知识) │  │ (教案/进度)    │  │
│  └─────┬─────┘  └──────┬────────┘  │
│        │               │           │
│  ┌─────▼───────────────▼────────┐  │
│  │    Behavior Decision Engine   │  │
│  │  ┌─────────────────────────┐ │  │
│  │  │ 1. 是否该发言？          │ │  │
│  │  │ 2. 发言类型？(提问/回答)  │ │  │
│  │  │ 3. 生成内容             │ │  │
│  │  └─────────────────────────┘ │  │
│  └──────────────┬───────────────┘  │
│                 │                   │
│  ┌──────────────▼───────────────┐  │
│  │    Conversation Memory        │  │
│  │  (短期: 当前对话上下文)        │  │
│  │  (长期: 本节课累积理解)        │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

#### Behavior Decision Engine — 发言决策

```python
# 伪代码：学生 Agent 的发言决策循环
async def student_tick(agent, teacher_utterance, lesson_progress):
    """每当教师说完一段话，触发所有学生 Agent 的决策"""
    
    # 1. 根据人设计算"发言意愿"
    speak_probability = calculate_speak_intent(
        persona=agent.persona,           # 积极型 → 高概率
        lesson_phase=lesson_progress,     # 演示阶段 → 适合提问
        time_since_last_speak=agent.last_spoke,
        confusion_level=agent.confusion,  # 越困惑越可能提问
    )
    
    # 2. 掷骰子决定是否发言
    if random.random() > speak_probability:
        return None  # 保持沉默
    
    # 3. 决定发言类型
    action_type = decide_action_type(
        teacher_utterance=teacher_utterance,
        is_question_asked=detect_question(teacher_utterance),
        persona=agent.persona,
    )
    
    # 4. 生成发言内容
    response = await llm_generate(
        system_prompt=agent.system_prompt,
        context=[
            agent.lesson_context,
            agent.conversation_memory,
            teacher_utterance,
        ],
        action_type=action_type,  # "ask_question" | "answer" | "express_confusion"
    )
    
    return response
```

#### System Prompt 模板

```
你是一个名叫{name}的学生，正在上一节关于"{lesson_title}"的课。

你的性格特征：{traits}
你的知识水平：{knowledge_level}
你的行为倾向：{behavior_description}

当前课程进度：教师正在讲解"{current_topic}"

规则：
1. 你只能以学生的身份发言
2. 你的提问应该符合你的知识水平（不要问太超前或太简单的问题）
3. 你的语气要符合你的性格（害羞的学生说话犹豫，积极的学生直接提问）
4. 回答要简短自然，像真实课堂中的学生一样（通常 1-3 句话）
5. 如果教师问了一个问题，根据你的知识水平决定是否能正确回答
```

### 4.3 模块三：实时语音管线（Audio Pipeline）

MVP 分为两个阶段实现：

#### 阶段 1：文字聊天（最快上线）

```
教师说话 → 麦克风 → STT → 文字 → Agent 处理 → 文字回复 → 显示在面板
```

- 教师在面板中看到学生的文字消息
- 教师可以打字回复，也可以语音回复（语音自动转文字）
- 延迟要求低，技术风险小

#### 阶段 2：语音交互（核心体验）

```
教师说话 → 麦克风 → STT → 文字 → Agent 处理 → TTS → 学生语音播放
                                                    ↑
                                              不同学生用不同声线
```

**音频流技术细节**：

```
┌──────────┐    PCM 16kHz     ┌───────────┐   文字   ┌──────────┐
│ 浏览器    │ ──WebSocket──▶  │ STT 服务   │ ──────▶ │ Agent    │
│ Web Audio │                 │ (Whisper)  │         │ 编排器   │
│ API       │                 └───────────┘         └────┬─────┘
└──────────┘                                             │
     ▲                                                   │ 回复文字
     │              PCM 24kHz     ┌───────────┐         │
     └──────WebSocket────────────│ TTS 服务   │◀────────┘
                                  │ (OpenAI)   │
                                  └───────────┘
```

#### 阶段 3：OpenAI Realtime API（终极方案）

```
教师说话 → 麦克风 → WebRTC → OpenAI Realtime API → 学生语音直接输出
```

- 使用 `gpt-realtime` 模型实现端到端语音对话
- 延迟 < 1 秒，体验最自然
- 每个学生 Agent 开一个独立的 Realtime Session，配置不同 voice
- 限制：单次 session 最长 60 分钟，需要 session 续接逻辑

### 4.4 模块四：Orchestrator（编排器）

编排器是系统的核心枢纽，负责协调多个学生 Agent 的发言时序。

```python
class SessionOrchestrator:
    """管理一次模拟课堂会话"""
    
    def __init__(self, lesson_config, student_agents):
        self.lesson = lesson_config
        self.agents = student_agents        # List[StudentAgent]
        self.timeline = []                  # 课堂时间线
        self.speaking_queue = asyncio.Queue()
        
    async def on_teacher_utterance(self, text: str, audio_clip: bytes):
        """教师说了一段话后触发"""
        
        # 更新课程进度上下文
        self.lesson.update_progress(text)
        
        # 并行触发所有学生 Agent 的决策
        responses = await asyncio.gather(*[
            agent.tick(text, self.lesson.progress)
            for agent in self.agents
        ])
        
        # 过滤掉沉默的学生
        active_responses = [r for r in responses if r is not None]
        
        # 防止多人同时说话：排队 + 随机延迟
        for resp in active_responses:
            delay = random.uniform(0.5, 3.0)  # 模拟真实反应时间
            await self.speaking_queue.put((delay, resp))
        
        # 按延迟顺序播放
        await self.play_responses()
        
        # 记录到时间线
        self.timeline.append({
            "timestamp": time.time(),
            "teacher": text,
            "student_responses": active_responses,
        })
```

**关键设计点**：
1. **防止抢话**：使用发言队列 + 随机延迟，避免所有学生同时说话
2. **发言频率控制**：全局参数控制每分钟最多几个学生发言
3. **上下文共享**：所有 Agent 共享 lesson_progress，但各自维护独立记忆
4. **教师点名**：检测教师话语中的学生名字，强制该学生回应

### 4.5 模块五：会话录制与回放（Session Recorder）

```
录制内容：
├── 教师音频流（完整录音）
├── 教师转写文字（带时间戳）
├── AI 学生发言记录（带时间戳）
├── 课程进度事件（章节切换时间点）
└── 屏幕截图 / 关键帧（可选，进阶功能）
```

**存储格式**：

```json
{
  "session_id": "sess_20260416_001",
  "lesson_id": "lesson_python_vars",
  "duration_seconds": 2700,
  "teacher_id": "teacher_001",
  "timeline": [
    {
      "t": 0,
      "type": "teacher_speech",
      "text": "同学们好，今天我们来学习 Python 的变量",
      "audio_url": "s3://recordings/sess_001/chunk_0.wav"
    },
    {
      "t": 15,
      "type": "student_response",
      "student": "小明",
      "text": "老师好！变量是不是就像数学里的 x？",
      "action_type": "ask_question"
    },
    {
      "t": 22,
      "type": "teacher_speech",
      "text": "小明问得好！变量确实类似数学中的未知数...",
      "audio_url": "s3://recordings/sess_001/chunk_1.wav"
    }
  ]
}
```

### 4.6 模块六：教学分析器（Teaching Analyzer）

课后分析教师表现，生成结构化反馈报告。

#### 分析维度

| 维度 | 分析内容 | 数据来源 |
|------|----------|----------|
| **教学节奏** | 每个环节实际 vs 计划用时 | 时间线 + 教案 |
| **互动质量** | 是否回应了学生问题、回应方式 | 对话记录 |
| **知识覆盖** | 教案中的知识点是否都讲到了 | 教师转写 vs 教案 |
| **提问技巧** | 提问的开放性、层次性、候答时间 | 教师转写分析 |
| **课堂管理** | 是否关注到不同类型的学生 | 点名/互动分布 |
| **语言清晰度** | 语速、填充词、专业术语使用 | 音频分析 |

#### 分析报告示例

```markdown
# 教学分析报告

## 课程信息
- 课题：Python 变量与数据类型
- 时长：42 分钟（计划 45 分钟）

## 总体评价：B+

### ✅ 亮点
1. **开场有效**：用"数学中的未知数"类比引入变量概念，学生理解度高
2. **互动及时**：对小明的追问给予了深入回答
3. **知识覆盖完整**：教案中 5 个核心知识点全部涉及

### ⚠️ 改进建议
1. **互动分布不均**：与小明互动 8 次，与小红仅 1 次，小刚 0 次
   → 建议主动关注安静/走神的学生
2. **演示节奏偏快**：IDE 演示阶段仅用 10 分钟（计划 15 分钟）
   → 建议放慢速度，增加"你们看到了什么？"等引导问题
3. **候答时间不足**：提问后平均 1.2 秒就给出答案
   → 建议等待 3-5 秒让学生思考

### 📊 详细数据
| 指标 | 数值 |
|------|------|
| 教师说话占比 | 78% |
| 学生发言次数 | 12 次 |
| 提问次数 | 6 次 |
| 平均候答时间 | 1.2 秒 |
| 知识点覆盖率 | 100% |
```

**技术实现**：
- 将完整的 session timeline 发送给 LLM（GPT-4o / Claude）
- 使用结构化 prompt 生成各维度评分和建议
- 与教案的原始计划进行对比分析

---

## 5. MVP 分阶段交付计划

### Phase 0：技术验证（Tech Spike）

**目标**：验证核心技术可行性，产出可运行 demo。

| 任务 | 产出 |
|------|------|
| ClassIn API 对接 | 能通过 API 创建课程、添加虚拟学生、获取课堂信息 |
| 单个 Student Agent | 1 个 LLM Agent 能根据教案和教师输入生成合理回复 |
| 浏览器音频采集 | Web Audio API 采集麦克风 → 流式传输到后端 |
| STT pipeline | Whisper API 流式转写教师语音 |
| 端到端 demo | 教师说话 → STT → Agent 回复 → 显示文字（单学生） |

**技术风险点**：
- ClassIn API 是否允许创建虚拟学生账号（可能需要与 ClassIn 商务沟通）
- 浏览器能否捕获系统音频（通常只能捕获麦克风，系统音频需要 screen capture API）
- STT 流式延迟是否可接受

### Phase 1：MVP v1 — 文字交互版

**目标**：完整的文字交互版本，教师通过语音或打字与多个 AI 学生互动。

```
┌─────────────────────────────────────────────────────┐
│          Student Panel (浏览器)                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │  📋 课程：Python 变量与数据类型  ⏱ 12:35       │ │
│  ├─────────────────────────────────────────────────┤ │
│  │                                                 │ │
│  │  👨‍🏫 老师：今天我们来学习 Python 的变量...      │ │
│  │                                                 │ │
│  │  🙋 小明：老师，变量是不是就像数学里的 x？      │ │
│  │                                                 │ │
│  │  👨‍🏫 老师：对，可以这么理解...                   │ │
│  │                                                 │ │
│  │  😕 小刚：等一下，什么是变量？                  │ │
│  │                                                 │ │
│  ├─────────────────────────────────────────────────┤ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐                    │ │
│  │  │小明 😊│ │小红 😶│ │小刚 😴│  ← 学生状态      │ │
│  │  │活跃   │ │安静   │ │走神   │                    │ │
│  │  └──────┘ └──────┘ └──────┘                    │ │
│  ├─────────────────────────────────────────────────┤ │
│  │  🎤 [语音输入] | 💬 [文字输入...]  [发送]       │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**功能清单**：

| # | 功能 | 优先级 |
|---|------|--------|
| 1 | 教案上传与解析 | P0 |
| 2 | 学生角色配置（预设模板 + 自定义） | P0 |
| 3 | 多学生 Agent 并行运行 | P0 |
| 4 | 教师麦克风 → STT → 文字显示 | P0 |
| 5 | Agent 自动发言 + 教师文字回复 | P0 |
| 6 | 发言排队与时序控制 | P1 |
| 7 | 会话时间线记录 | P1 |
| 8 | 基础教学分析报告 | P1 |
| 9 | ClassIn API 课程创建集成 | P2 |
| 10 | 会话回放功能 | P2 |

**技术任务拆解**：

```
后端 (Python/FastAPI):
├── models/          # 数据模型
│   ├── lesson.py    # 教案模型
│   ├── student.py   # 学生配置模型
│   └── session.py   # 会话模型
├── agents/
│   ├── student_agent.py      # 学生 Agent 核心逻辑
│   ├── behavior_engine.py    # 发言决策引擎
│   └── prompt_templates.py   # Prompt 模板
├── services/
│   ├── orchestrator.py       # 会话编排器
│   ├── stt_service.py        # 语音转文字服务
│   ├── tts_service.py        # 文字转语音服务（Phase 2）
│   ├── classin_service.py    # ClassIn API 集成
│   └── analyzer_service.py   # 教学分析服务
├── api/
│   ├── lesson_routes.py      # 教案 CRUD
│   ├── session_routes.py     # 会话管理
│   └── ws_handler.py         # WebSocket 处理
└── core/
    ├── config.py
    └── database.py

前端 (React/TypeScript):
├── components/
│   ├── LessonSetup/          # 教案配置页
│   ├── StudentPanel/         # 学生互动面板
│   │   ├── ChatTimeline.tsx  # 对话时间线
│   │   ├── StudentCard.tsx   # 学生状态卡片
│   │   └── AudioInput.tsx    # 语音输入组件
│   ├── SessionReport/        # 教学分析报告页
│   └── common/
├── hooks/
│   ├── useWebSocket.ts       # WebSocket hook
│   └── useAudioCapture.ts    # 音频采集 hook
└── services/
    └── api.ts
```

### Phase 2：MVP v2 — 语音交互版

**目标**：在文字版基础上增加 TTS，AI 学生能"说话"。

**新增功能**：

| # | 功能 | 说明 |
|---|------|------|
| 1 | TTS 语音输出 | 每个学生有独特声线 |
| 2 | 语音播放队列 | 防止多学生同时说话 |
| 3 | 教师语音直接对话 | 全程语音交互，无需打字 |
| 4 | 课堂录音 | 完整录制教师+AI学生的音频 |

**TTS 声线分配策略**：

```python
VOICE_PROFILES = {
    "积极主动型": {"voice": "alloy", "speed": 1.1, "pitch": "high"},
    "害羞安静型": {"voice": "nova", "speed": 0.9, "pitch": "low"},
    "容易走神型": {"voice": "echo", "speed": 1.0, "pitch": "medium"},
    "学霸型":     {"voice": "fable", "speed": 1.0, "pitch": "medium"},
    "好奇宝宝型": {"voice": "shimmer", "speed": 1.2, "pitch": "high"},
}
```

### Phase 3：进阶功能

| 功能 | 说明 |
|------|------|
| OpenAI Realtime API | 端到端语音对话，延迟 < 1 秒 |
| 屏幕理解 | 通过截屏 + Vision API 理解教师正在演示的内容 |
| ClassIn SDK 深度集成 | 一体化体验，AI 学生出现在 ClassIn 教室内 |
| 多教师协作 | 多个教师共享学生配置和分析报告 |
| 历史会话对比 | 同一教案多次教学的对比分析 |
| 学生行为库 | 基于真实课堂数据训练的学生行为模型 |

---

## 6. 数据模型

### 6.1 核心 ER 图

```
┌──────────────┐     1:N     ┌──────────────────┐
│   Teacher     │────────────│   Lesson          │
│──────────────│            │──────────────────│
│ id           │            │ id               │
│ name         │            │ teacher_id       │
│ email        │            │ title            │
└──────────────┘            │ script (text)    │
                            │ key_concepts[]   │
                            │ duration_min     │
                            └────────┬─────────┘
                                     │ 1:N
                            ┌────────▼─────────┐
                            │ StudentConfig     │
                            │──────────────────│
                            │ id               │
                            │ lesson_id        │
                            │ name             │
                            │ persona_type     │
                            │ traits (text)    │
                            │ knowledge_level  │
                            └──────────────────┘

┌──────────────┐     1:N     ┌──────────────────┐
│   Session     │────────────│  TimelineEvent    │
│──────────────│            │──────────────────│
│ id           │            │ id               │
│ lesson_id    │            │ session_id       │
│ started_at   │            │ timestamp_ms     │
│ ended_at     │            │ event_type       │
│ status       │            │ speaker          │
│ recording_url│            │ content (text)   │
└──────┬───────┘            │ audio_url        │
       │ 1:1                │ metadata (json)  │
       │                    └──────────────────┘
┌──────▼───────┐
│ AnalysisReport│
│──────────────│
│ id           │
│ session_id   │
│ overall_score│
│ dimensions[] │
│ highlights[] │
│ suggestions[]│
│ raw_data     │
└──────────────┘
```

---

## 7. API 设计

### 7.1 REST API

```
# 教案管理
POST   /api/lessons                    # 创建教案
GET    /api/lessons                    # 教案列表
GET    /api/lessons/:id                # 获取教案详情
PUT    /api/lessons/:id                # 更新教案
DELETE /api/lessons/:id                # 删除教案

# 学生配置
POST   /api/lessons/:id/students       # 添加学生配置
GET    /api/lessons/:id/students       # 获取学生列表
PUT    /api/students/:id               # 更新学生配置
DELETE /api/students/:id               # 删除学生

# 会话管理
POST   /api/sessions                   # 创建新会话（开始上课）
GET    /api/sessions/:id               # 获取会话详情
POST   /api/sessions/:id/end           # 结束会话
GET    /api/sessions/:id/timeline      # 获取会话时间线
GET    /api/sessions/:id/recording     # 获取录音

# 教学分析
POST   /api/sessions/:id/analyze       # 触发分析
GET    /api/sessions/:id/report        # 获取分析报告

# 模板
GET    /api/templates/students         # 预设学生模板
```

### 7.2 WebSocket 事件

```typescript
// 客户端 → 服务端
interface ClientEvents {
  "session:start":       { session_id: string }
  "teacher:text":        { text: string }
  "teacher:audio_chunk": { audio: ArrayBuffer, sample_rate: number }
  "teacher:audio_end":   {}  // VAD 检测到教师停止说话
  "teacher:point_student": { student_name: string }  // 教师点名
}

// 服务端 → 客户端
interface ServerEvents {
  "session:ready":        { session_id: string, students: StudentInfo[] }
  "teacher:transcription": { text: string, is_final: boolean }
  "student:typing":       { student_name: string }  // 学生正在"思考"
  "student:message":      { student_name: string, text: string, type: string }
  "student:audio":        { student_name: string, audio: ArrayBuffer }
  "student:state_change": { student_name: string, state: string }  // 状态变化
  "session:error":        { code: string, message: string }
}
```

---

## 8. 部署架构

### MVP 部署（单机 / 小规模）

```
┌─────────────────────────────────────────────┐
│           Docker Compose                     │
│  ┌──────────────┐  ┌──────────────────────┐ │
│  │ nginx        │  │ frontend (React)     │ │
│  │ (reverse     │  │ :3000                │ │
│  │  proxy + SSL)│  └──────────────────────┘ │
│  │ :443         │  ┌──────────────────────┐ │
│  └──────────────┘  │ backend (FastAPI)    │ │
│                    │ :8000                │ │
│  ┌──────────────┐  │ + WebSocket          │ │
│  │ PostgreSQL   │  └──────────────────────┘ │
│  │ :5432        │  ┌──────────────────────┐ │
│  └──────────────┘  │ Redis                │ │
│  ┌──────────────┐  │ :6379                │ │
│  │ MinIO (S3)   │  └──────────────────────┘ │
│  │ :9000        │                            │
│  └──────────────┘                            │
└─────────────────────────────────────────────┘
```

---

## 9. 关键技术风险与缓解

| # | 风险 | 影响 | 缓解策略 |
|---|------|------|----------|
| 1 | **ClassIn 不支持虚拟学生** | AI 学生无法出现在 ClassIn 教室内 | MVP 用独立面板方案，不依赖 ClassIn 内部机制 |
| 2 | **LLM 延迟过高** | 学生回复不够实时 | 使用流式响应（streaming）；优先用 GPT-4o-mini 降低延迟 |
| 3 | **多 Agent 并发成本** | 3-5 个 Agent 同时推理，token 消耗大 | 控制 context window 大小；使用轻量模型做发言决策 |
| 4 | **STT 流式延迟** | 教师说话到文字显示延迟大 | 使用 Deepgram（延迟 < 300ms）或 Whisper 流式模式 |
| 5 | **浏览器音频权限** | 用户可能拒绝麦克风权限 | 清晰的权限引导 UI；提供文字输入作为 fallback |
| 6 | **学生发言不自然** | LLM 生成的学生回复太"AI" | 精心设计 persona prompt；few-shot 示例；人工评审迭代 |
| 7 | **教学分析质量** | 分析报告空洞、不实用 | 与真实教师合作设计分析维度；迭代 prompt |

---

## 10. 成本估算（MVP 运行时）

| 资源 | 单位成本 | 单节课用量（45 分钟） | 估算费用 |
|------|----------|----------------------|----------|
| STT (Whisper) | $0.006/分钟 | 45 分钟 | ~$0.27 |
| LLM (GPT-4o-mini) | ~$0.15/1M input, $0.60/1M output | ~50K tokens | ~$0.04 |
| LLM (GPT-4o) 分析报告 | ~$2.50/1M input | ~30K tokens | ~$0.08 |
| TTS (OpenAI) | $15/1M chars | ~5000 chars | ~$0.08 |
| 服务器 | ~$50/月 | - | ~$0.07/节 |
| **合计** | | | **~$0.54/节课** |

> 注：使用 OpenAI Realtime API 时费用约为 $0.065/分钟（音频），45 分钟约 $2.93/节课，但延迟体验大幅提升。

---

## 11. 开发优先级总结

```
Phase 0 (Tech Spike)
  │  验证：ClassIn API / STT / 单 Agent 对话
  ▼
Phase 1 (MVP v1 - 文字版)
  │  核心功能：教案配置 → 多学生 Agent → 文字互动 → 基础分析
  │  这是可以演示给利益相关者的最小可用版本
  ▼
Phase 2 (MVP v2 - 语音版)
  │  增强体验：TTS 语音输出 → 全程语音交互 → 录制
  ▼
Phase 3 (进阶)
  │  Realtime API / 屏幕理解 / ClassIn SDK 深度集成
  ▼
Beyond MVP
     多教师 / 历史对比 / 真实学生行为训练
```

---

## 12. 立即可以开始的行动

1. **申请 ClassIn PaaS API 权限**：联系 ClassIn 商务获取 SID/SECRET
2. **搭建项目脚手架**：FastAPI + React + Docker Compose
3. **实现单个 Student Agent 原型**：用 GPT-4o-mini + 固定教案测试对话质量
4. **浏览器音频采集 POC**：验证 Web Audio API 采集 + WebSocket 流式传输
5. **参考 EducaSim 论文**：学习其 Agent 架构设计和课堂部署经验
