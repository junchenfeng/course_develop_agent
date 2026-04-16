# AI 模拟学生备课系统 — MVP 技术路线图

> 版本: v0.2 · 2026-04-16
> 状态: 产品设计已对齐，待进入开发

---

## 1. 产品定义

### 1.1 一句话描述

CLI 驱动的本地备课练习工具：新手教师通过语音与 AI 模拟学生互动，练习授课技能，课后获得自动化教学反馈。

### 1.2 核心用户故事

```
作为一名新手教师，我希望：
1. 编写一份 YAML 格式的教案（含时间规划、知识点、学生角色、预设问题）
2. 用 CLI 启动一次模拟练课
3. 在 PC 上一边操作 PPT / Chrome 演示教学内容，一边与旁边终端里的 AI 学生互动
4. 全程用语音授课，AI 学生以文字形式提问和回答
5. 练课结束后，系统自动生成分析报告：
   - 我是否按教案的时间规划完整地执行了每个环节
   - 我面对学生预设问题时的回答质量如何
```

### 1.3 系统约束

| 约束 | 说明 |
|------|------|
| 运行环境 | 教师本地 PC（Windows/macOS），CLI 启动 |
| 教师交互 | 仅语音（麦克风），不打字 |
| 学生交互 | 仅文字输出到终端/面板，不发语音 |
| 教师演示 | 教师自行在本地打开 PPT 和 Chrome，系统不嵌入这些应用 |
| 录制内容 | 教师音频 + 屏幕录制（不录摄像头） |
| 不依赖 ClassIn | MVP 阶段完全独立，不对接任何第三方教室平台 |

### 1.4 目标用户

| 用户类型 | 场景 |
|----------|------|
| **新手教师**（主要） | 刚入职，需要反复练习一节课的授课流程和应变能力 |
| **培训师/开发者**（次要） | 验证教案设计质量，以身试教，迭代教案 |

---

## 2. 使用流程

### 2.1 教师 PC 桌面布局

```
┌────────────────────────────────┬─────────────────────────┐
│                                │                         │
│   PowerPoint / Chrome          │   终端（AI 学生面板）    │
│   （教师自行打开和操作）         │                         │
│                                │   ┌───────────────────┐ │
│   ┌──────────────────────┐     │   │ [05:32] 📋 环节2   │ │
│   │                      │     │   │ 新课导入:什么是变量 │ │
│   │   教师的 PPT 或       │     │   │                   │ │
│   │   浏览器演示内容       │     │   │ 🙋 小明:          │ │
│   │                      │     │   │ 老师，变量和常量   │ │
│   │                      │     │   │ 有什么区别？       │ │
│   │                      │     │   │                   │ │
│   └──────────────────────┘     │   │ 😕 小刚:          │ │
│                                │   │ 什么是变量啊，没   │ │
│                                │   │ 太听懂...         │ │
│                                │   └───────────────────┘ │
│                                │   🎤 教师正在说话...     │
└────────────────────────────────┴─────────────────────────┘
              ↓ 系统后台同时进行
      麦克风音频录制 + 屏幕录制 + STT + Agent 交互记录
```

### 2.2 端到端流程

```
准备阶段:
  教师编写 lesson.yaml ──→ CLI 验证教案格式

启动阶段:
  $ teachsim start lesson.yaml
  ──→ 加载教案 + 初始化 Student Agents
  ──→ 开始录制（麦克风 + 屏幕）
  ──→ 开始 STT 流式识别
  ──→ 终端显示 "练课开始，请开始授课"

授课阶段 (20 分钟):
  教师语音 ──→ SeedASR 实时转写 ──→ Orchestrator
     ├──→ 更新课程进度追踪（当前在哪个环节）
     ├──→ 触发 Student Agent 决策（是否发言 / 提出预设问题）
     └──→ 学生文字回复显示在终端

  教师看到学生文字 ──→ 用语音回应 ──→ 系统记录教师的回应

结束阶段:
  $ Ctrl+C 或教案时间到
  ──→ 停止录制
  ──→ 保存 session 数据（时间线 JSON + 音频 + 屏幕录像）

分析阶段:
  $ teachsim analyze <session_id>
  ──→ LLM 分析 session timeline vs 教案
  ──→ 输出分析报告（Markdown 文件）
```

---

## 3. 教案 YAML Schema

```yaml
# lesson.yaml — 教案配置文件

lesson:
  title: "Python 变量与数据类型"
  duration_minutes: 20

  # 教学环节（按时间顺序），Analyzer 依据此检查执行情况
  phases:
    - name: "开场复习"
      duration_minutes: 3
      description: "复习上节课 print() 函数的用法"
      key_points:
        - "print() 的基本语法"
        - "字符串拼接"

    - name: "新课导入"
      duration_minutes: 5
      description: "引入变量的概念，解释为什么需要变量"
      key_points:
        - "变量是存储数据的容器"
        - "变量命名规则"
        - "赋值运算符 ="

    - name: "代码演示"
      duration_minutes: 7
      description: "在 IDE 中演示变量的定义和使用"
      key_points:
        - "整数和浮点数变量"
        - "字符串变量"
        - "type() 函数查看类型"
        - "变量的重新赋值"

    - name: "互动练习"
      duration_minutes: 3
      description: "让学生预测代码输出结果"
      key_points:
        - "变量覆盖"
        - "类型转换"

    - name: "总结"
      duration_minutes: 2
      description: "回顾本节课重点，预告下节课内容"
      key_points:
        - "变量的作用"
        - "四种基本数据类型"

  # 预设问题：AI 学生会在合适的时机提出，Analyzer 检查教师回答质量
  preset_questions:
    - question: "老师，变量和常量有什么区别？"
      expected_phase: "新课导入"
      reference_answer: "变量的值可以改变，常量的值不能改变。Python 中没有严格的常量语法，通常用全大写命名表示常量。"
      difficulty: "medium"
      asked_by: "小明"

    - question: "为什么 x = 1 之后再写 x = 2，x 就变成 2 了？之前的 1 去哪了？"
      expected_phase: "代码演示"
      reference_answer: "变量名就像一个标签，x = 1 是把标签贴在 1 上，x = 2 是把标签撕下来贴到 2 上。原来的 1 如果没有其他变量指向它，Python 会自动回收这块内存。"
      difficulty: "medium"
      asked_by: "小明"

    - question: "老师，我没太听懂变量是什么，能再解释一下吗？"
      expected_phase: "新课导入"
      reference_answer: "可以把变量想象成一个盒子，盒子上写着名字，里面可以放东西。比如 age = 18，就是一个叫 age 的盒子里放了 18 这个数字。"
      difficulty: "easy"
      asked_by: "小刚"

    - question: "type() 函数除了查看类型，还能做什么？"
      expected_phase: "代码演示"
      reference_answer: "type() 主要就是用来查看数据类型。在调试时很有用，可以帮你确认一个变量到底是什么类型。进阶用法中还可以用 type() 动态创建类，但这是高级内容。"
      difficulty: "hard"
      asked_by: "小明"

# 学生角色配置
students:
  - name: "小明"
    persona: "积极主动型"
    traits: |
      经常举手提问，理解力强，喜欢追问底层原理。
      会在教师讲完一个知识点后主动提出相关问题。
      偶尔会提出超纲问题。
    knowledge_level: "中等偏上"

  - name: "小红"
    persona: "认真沉默型"
    traits: |
      很少主动发言，但被点名时能给出正确答案。
      偶尔会在聊天中打出"嗯嗯"、"明白了"等简短回应。
      如果教师讲得不清楚会小声说"没太听懂"。
    knowledge_level: "中等"

  - name: "小刚"
    persona: "容易走神型"
    traits: |
      注意力不集中，会在教师已经讲过一个话题后又问相同的问题。
      有时候会问跟课程无关的问题。
      但如果教师耐心解释，他能够理解。
    knowledge_level: "中等偏下"
```

---

## 4. 整体架构

### 4.1 MVP 架构（CLI 驱动，本地运行）

```
                          教师 PC
┌───────────────────────────────────────────────────────┐
│                                                       │
│  ┌─────────────┐   ┌──────────────────────────────┐  │
│  │ PPT / Chrome │   │  teachsim CLI                │  │
│  │ (教师自行操作)│   │                              │  │
│  └─────────────┘   │  ┌────────────────────────┐  │  │
│                     │  │ Terminal UI            │  │  │
│  ┌─────────────┐   │  │ (学生消息 + 状态显示)   │  │  │
│  │ 🎤 麦克风    │──▶│  └────────────────────────┘  │  │
│  └─────────────┘   │                              │  │
│                     │  ┌────────────────────────┐  │  │
│  ┌─────────────┐   │  │ 录制模块               │  │  │
│  │ 🖥 屏幕      │──▶│  │ (音频 + 屏幕)          │  │  │
│  └─────────────┘   │  └────────────────────────┘  │  │
│                     └──────────┬───────────────────┘  │
│                                │                      │
└────────────────────────────────┼──────────────────────┘
                                 │ 音频流
                                 ▼
                    ┌─────────────────────────┐
                    │   SeedASR (火山引擎)     │
                    │   WebSocket 流式 STT     │
                    └────────────┬────────────┘
                                 │ 实时转写文字
                                 ▼
              ┌──────────────────────────────────────┐
              │         本地 Python 进程               │
              │                                      │
              │  ┌──────────────────────────────────┐│
              │  │        Orchestrator               ││
              │  │  ┌────────┐ ┌──────────────────┐ ││
              │  │  │Progress│ │ Question          │ ││
              │  │  │Tracker │ │ Scheduler         │ ││
              │  │  └────────┘ └──────────────────┘ ││
              │  └──────────┬───────────────────────┘│
              │             │                        │
              │  ┌──────────▼───────────────────────┐│
              │  │      Student Agent Pool           ││
              │  │  ┌────────┐┌────────┐┌────────┐  ││
              │  │  │ 小明    ││ 小红    ││ 小刚    │  ││
              │  │  │ Agent  ││ Agent  ││ Agent  │  ││
              │  │  └────────┘└────────┘└────────┘  ││
              │  └──────────────────────────────────┘│
              │             │ LLM API calls          │
              │             ▼                        │
              │  ┌──────────────────────────────────┐│
              │  │  LLM Service                      ││
              │  │  (GPT-4o-mini / Seed 2.0 Lite)   ││
              │  └──────────────────────────────────┘│
              │                                      │
              │  ┌──────────────────────────────────┐│
              │  │  Session Recorder                 ││
              │  │  (timeline.json + audio + screen) ││
              │  └──────────────────────────────────┘│
              └──────────────────────────────────────┘

课后分析（离线）:
              ┌──────────────────────────────────────┐
              │  $ teachsim analyze <session_id>      │
              │                                      │
              │  timeline.json + lesson.yaml          │
              │         │                            │
              │         ▼                            │
              │  ┌──────────────────────────────────┐│
              │  │  Teaching Analyzer               ││
              │  │  (LLM: GPT-4o / Claude)          ││
              │  │                                  ││
              │  │  1. 教案执行检查                   ││
              │  │  2. 预设问题回答检查               ││
              │  └──────────────┬───────────────────┘│
              │                 │                    │
              │                 ▼                    │
              │        report_<session_id>.md         │
              └──────────────────────────────────────┘
```

### 4.2 技术栈

| 层级 | 技术选择 | 说明 |
|------|----------|------|
| **CLI 框架** | Python + `click` 或 `typer` | 命令行入口 |
| **终端 UI** | `rich` / `textual` | 在终端中显示学生消息和课程状态 |
| **STT** | SeedASR（火山引擎大模型流式语音识别） | WebSocket 流式，中文识别质量好 |
| **LLM（Agent）** | GPT-4o-mini / Seed 2.0 Lite | 学生角色扮演，低延迟 |
| **LLM（分析）** | GPT-4o / Claude | 课后教学分析，需要强推理 |
| **音频采集** | `pyaudio` / `sounddevice` | 本地麦克风录制 |
| **屏幕录制** | `mss` + `ffmpeg` | 截屏序列 → 视频 |
| **数据存储** | 本地文件系统（JSON + WAV + MP4） | MVP 不需要数据库 |
| **配置格式** | YAML | 教案和学生配置 |

---

## 5. 核心模块设计

### 5.1 STT 服务（SeedASR 接入）

```
教师麦克风 ──→ pyaudio 采集 PCM 16kHz
                    │
                    │ 每 200ms 发送一个音频包
                    ▼
          WebSocket 连接到 SeedASR
          wss://openspeech.bytedance.com/api/v3/sauc/bigmodel
                    │
                    │ 返回流式转写结果
                    ▼
              {text: "今天我们来学习变量", is_final: true}
                    │
                    ▼
              发送给 Orchestrator
```

**关键参数**：
- 采样率: 16000 Hz
- 单包音频: 200ms
- 发包间隔: 100-200ms
- 鉴权: 火山引擎 AppID + Token

**Fallback 方案**：如果 SeedASR 接入受阻（如审批延迟），可快速切换到：
- Deepgram Nova-3（$0.0077/min，支持中文，有 $200 免费额度）
- OpenAI Whisper（$0.006/min，需要自行做流式分片）

### 5.2 Student Agent

每个 AI 学生是一个独立的 LLM 对话实例，通过 system prompt 定义人设。

#### Agent 状态机

```
                ┌──────────┐
                │  IDLE    │ 默认状态，在"听课"
                └────┬─────┘
                     │ 教师说了一段话
                     ▼
              ┌──────────────┐
              │  EVALUATING  │ 决策：是否该发言？
              └──────┬───────┘
                     │
            ┌────────┼────────┐
            ▼        ▼        ▼
      ┌─────────┐ ┌──────┐ ┌──────────────┐
      │ RESPOND │ │ IDLE │ │ ASK_PRESET_Q │
      │ (自由回应)│ │(沉默) │ │ (提预设问题)  │
      └────┬────┘ └──────┘ └──────┬───────┘
           │                      │
           └──────────┬───────────┘
                      ▼
               ┌────────────┐
               │ WAITING    │ 等待教师回应
               └────────────┘
```

#### 决策逻辑

```python
async def agent_decide(agent, teacher_text, orchestrator_context):
    """一个 Agent 在教师说完一段话后的决策"""

    # 1. 是否是被点名了？
    if agent.name in teacher_text:
        return await agent.generate_response(teacher_text, forced=True)

    # 2. Orchestrator 是否调度了预设问题？
    scheduled_q = orchestrator_context.get_scheduled_question(agent.name)
    if scheduled_q:
        return AgentAction(
            type="preset_question",
            text=scheduled_q["question"],
        )

    # 3. 根据人设计算自由发言概率
    speak_prob = compute_speak_probability(
        persona=agent.persona,
        current_phase=orchestrator_context.current_phase,
        turns_since_last_spoke=agent.turns_silent,
        teacher_asked_question="?" in teacher_text,
    )

    if random.random() < speak_prob:
        return await agent.generate_free_response(teacher_text)

    # 4. 沉默，但可能发一个简短反应
    if random.random() < 0.1:
        return AgentAction(type="reaction", text="嗯嗯")

    return None
```

#### System Prompt

```
你是"{name}"，一个正在上编程课的学生。

## 你的性格
{traits}

## 你的知识水平
{knowledge_level}

## 当前课堂情况
- 课题：{lesson_title}
- 当前环节：{current_phase}（{phase_description}）
- 已过时间：{elapsed_minutes} 分钟

## 规则
1. 你只能以学生身份发言，用口语化的中文
2. 回答简短自然，1-2 句话，像真实课堂
3. 你的提问和回答必须符合你的知识水平
4. 你的语气必须符合你的性格
```

### 5.3 Orchestrator（编排器）

编排器的核心职责：
1. **进度追踪**：根据教师转写内容，判断当前处于教案的哪个环节
2. **预设问题调度**：在合适的环节触发预设问题
3. **Agent 协调**：收集所有 Agent 决策，排队输出，防止同时发言
4. **时间线记录**：记录所有事件到 timeline

```python
class Orchestrator:
    def __init__(self, lesson_config, agents):
        self.lesson = lesson_config
        self.agents = agents
        self.timeline = []
        self.current_phase_idx = 0
        self.phase_start_time = time.time()
        self.asked_questions = set()  # 已提出的预设问题索引
        self.start_time = time.time()

    async def on_teacher_utterance(self, text: str, timestamp: float):
        """教师每说完一句话（STT 返回 is_final=true 时触发）"""

        # 1. 记录教师发言
        self.timeline.append({
            "t": timestamp - self.start_time,
            "type": "teacher_speech",
            "text": text,
        })

        # 2. 更新课程进度
        self._update_phase_tracking(text, timestamp)

        # 3. 决定是否该提预设问题
        scheduled_question = self._maybe_schedule_preset_question()

        # 4. 触发所有 Agent 决策
        context = OrchestratorContext(
            current_phase=self.lesson.phases[self.current_phase_idx],
            scheduled_question=scheduled_question,
            elapsed=timestamp - self.start_time,
        )

        actions = await asyncio.gather(*[
            agent.decide(text, context) for agent in self.agents
        ])

        # 5. 过滤 + 排队输出
        active = [a for a in actions if a is not None]
        for action in active:
            delay = random.uniform(1.0, 4.0)
            await asyncio.sleep(delay)
            self._display_student_message(action)
            self.timeline.append({
                "t": time.time() - self.start_time,
                "type": "student_action",
                "student": action.student_name,
                "action_type": action.type,
                "text": action.text,
            })

    def _maybe_schedule_preset_question(self):
        """检查当前环节是否有未提出的预设问题"""
        current_phase_name = self.lesson.phases[self.current_phase_idx]["name"]
        for i, q in enumerate(self.lesson.preset_questions):
            if i not in self.asked_questions and q["expected_phase"] == current_phase_name:
                # 一定概率触发（不是每次教师说话都问）
                if random.random() < 0.3:
                    self.asked_questions.add(i)
                    return q
        return None
```

### 5.4 录制模块

MVP 录制三路数据：

| 数据 | 格式 | 工具 |
|------|------|------|
| 教师音频 | WAV (PCM 16kHz mono) | `sounddevice` 持续录制 |
| 屏幕录像 | MP4 (H.264) | `mss` 截屏 + `ffmpeg` 编码 |
| 交互时间线 | JSON | 内存中累积，结束时写文件 |

存储目录结构：

```
sessions/
  sess_20260416_143022/
    lesson.yaml           # 本次使用的教案副本
    timeline.json          # 完整时间线
    audio.wav              # 教师音频录制
    screen.mp4             # 屏幕录像
    report.md              # 分析报告（analyze 后生成）
```

### 5.5 教学分析器

两个分析功能，均通过 LLM 实现。

#### 功能 1：教案执行检查

**输入**：`lesson.yaml`（教案计划）+ `timeline.json`（实际执行）

**分析 Prompt 思路**：

```
你是一个教学观察专家。以下是一份教案计划和实际的课堂时间线记录。

## 教案计划
{lesson_yaml_phases}

## 实际课堂时间线
{timeline_json}

请分析：
1. 每个教案环节是否被执行了？（跳过 / 完成 / 部分完成）
2. 每个环节的实际用时 vs 计划用时
3. 各环节的知识点 key_points 是否在教师的讲解中被覆盖到
4. 环节之间的衔接是否流畅（是否有长时间停顿、跳跃、倒回）
5. 整体时间分配是否合理

输出格式：
- 总览表格：每个环节的计划时间 / 实际时间 / 完成度 / 知识点覆盖率
- 亮点（做得好的地方）
- 改进建议（具体、可操作）
```

#### 功能 2：预设问题回答检查

**输入**：`lesson.yaml`（含预设问题及参考答案）+ `timeline.json`（含教师实际回答）

**分析 Prompt 思路**：

```
你是一个教学评估专家。以下是课堂中学生提出的预设问题、参考答案，以及教师的实际回答。

## 预设问题列表
{preset_questions_with_reference}

## 教师的实际回答记录
{teacher_responses_to_questions}

请逐一评估教师的回答：
1. 准确性：教师的回答是否正确？与参考答案对比
2. 清晰度：教师的解释是否通俗易懂？适合学生水平？
3. 完整性：是否涵盖了参考答案的核心要点？
4. 应变能力：如果教师偏离了参考答案但回答合理，应给予正面评价

输出格式：
- 每个问题的评分（A/B/C/D）+ 点评
- 总体评价
- 建议教师加强的知识点
```

---

## 6. CLI 命令设计

```bash
# 验证教案格式
$ teachsim validate lesson.yaml

# 启动练课（核心命令）
$ teachsim start lesson.yaml
  # --no-screen    不录制屏幕（节省资源）
  # --stt deepgram 使用 Deepgram 而非 SeedASR
  # --llm gpt-4o-mini  指定 Agent 使用的模型

# 查看历史会话
$ teachsim sessions

# 分析一次练课
$ teachsim analyze <session_id>
  # --model gpt-4o  指定分析用的模型

# 查看分析报告
$ teachsim report <session_id>

# 回放一次练课的时间线（文字回放）
$ teachsim replay <session_id>
```

---

## 7. 成本估算（20 分钟一堂练课）

### 方案 A：SeedASR + GPT-4o-mini（推荐 MVP）

| 组件 | 计算 | 费用 |
|------|------|------|
| SeedASR STT | 20min ÷ 60 × ¥4/hr | ¥1.33 |
| GPT-4o-mini（3 个 Agent，~30 次推理，每次 ~1K tokens） | ~30K tokens × $0.6/1M output | ¥0.15 |
| GPT-4o 分析报告（1 次，~20K tokens input） | ~20K tokens × $2.5/1M | ¥0.40 |
| **合计** | | **~¥1.9/堂课** |

### 方案 B：Deepgram + GPT-4o-mini（备选）

| 组件 | 计算 | 费用 |
|------|------|------|
| Deepgram Nova-3 STT | 20min × $0.0077/min | ¥1.10 |
| GPT-4o-mini Agent | 同上 | ¥0.15 |
| GPT-4o 分析报告 | 同上 | ¥0.40 |
| **合计** | | **~¥1.7/堂课** |

> 注：Deepgram 有 $200 免费额度（约 430 小时），足够 MVP 测试。

### 方案 C：SeedASR + Seed 2.0 Lite（全字节方案）

| 组件 | 计算 | 费用 |
|------|------|------|
| SeedASR STT | 20min ÷ 60 × ¥4/hr | ¥1.33 |
| Seed 2.0 Lite Agent | ~30K tokens × ¥0.13/1M | ¥0.004 |
| GPT-4o 分析报告 | 同上 | ¥0.40 |
| **合计** | | **~¥1.7/堂课** |

> Seed 2.0 Lite 的 token 成本极低，但中文教学场景的角色扮演质量需要实测验证。

---

## 8. 项目目录结构

```
teachsim/
├── cli.py                    # CLI 入口 (typer)
├── config.py                 # 全局配置（API keys、模型选择等）
│
├── models/
│   ├── lesson.py             # 教案数据模型（从 YAML 解析）
│   └── session.py            # 会话数据模型
│
├── agents/
│   ├── student_agent.py      # Student Agent 核心
│   ├── prompts.py            # System prompt 模板
│   └── llm_client.py         # LLM API 调用封装（支持多 provider）
│
├── services/
│   ├── orchestrator.py       # 会话编排器
│   ├── stt/
│   │   ├── base.py           # STT 抽象接口
│   │   ├── seedasr.py        # SeedASR 实现
│   │   └── deepgram.py       # Deepgram 实现（fallback）
│   ├── recorder.py           # 音频 + 屏幕录制
│   └── analyzer.py           # 教学分析器
│
├── ui/
│   └── terminal.py           # 终端 UI（rich/textual）
│
├── examples/
│   └── python_variables.yaml # 示例教案
│
└── sessions/                 # 会话数据存储目录
    └── .gitkeep
```

---

## 9. 技术风险与缓解

| # | 风险 | 影响 | 缓解策略 |
|---|------|------|----------|
| 1 | **SeedASR 接入审批慢** | 无法启动 STT 开发 | 先用 Deepgram（有 $200 免费额度，SDK 成熟），SeedASR 就绪后切换 |
| 2 | **STT 断句不准** | 教师一句话被切成碎片，Agent 反应混乱 | 设置合理的 VAD 参数；累积到 is_final=true 才触发 Agent |
| 3 | **LLM 延迟** | 学生回复出现太慢（>5 秒） | 用 GPT-4o-mini（延迟 ~1-2 秒）；限制 context 长度；流式输出 |
| 4 | **Agent 角色扮演质量差** | 学生发言不自然、太"AI" | 精心设计 prompt + few-shot 示例；先用 GPT-4o 测试质量后再降级 |
| 5 | **环节识别不准** | Orchestrator 无法正确判断当前教学环节 | 结合关键词匹配 + 时间窗口双重判断；允许手动标记环节切换 |
| 6 | **屏幕录制性能** | 截屏编码占用大量 CPU，影响其他模块 | 降低帧率（5-10 fps）；用独立进程录制；提供 --no-screen 选项 |
| 7 | **预设问题时机不对** | 在错误的环节提出预设问题，破坏课堂节奏 | 绑定 expected_phase + 概率触发；教师可在 YAML 中设置触发条件 |

---

## 10. 开发路线

```
Phase 0: Tech Spike（验证核心技术）
  ├─ 任务 0.1: STT 接通（SeedASR 或 Deepgram）
  │   产出: 麦克风 → 实时转写文字显示在终端
  ├─ 任务 0.2: 单个 Student Agent 对话
  │   产出: 输入教师文字 → Agent 返回角色扮演回复
  └─ 任务 0.3: 录制 POC
      产出: 同时录制麦克风音频 + 屏幕截图

Phase 1: MVP 主线功能
  ├─ 任务 1.1: YAML 教案解析 + 验证
  ├─ 任务 1.2: Orchestrator（进度追踪 + 预设问题调度）
  ├─ 任务 1.3: 多 Agent 并行 + 发言排队
  ├─ 任务 1.4: 终端 UI（rich 显示学生消息 + 课程状态）
  ├─ 任务 1.5: Session 录制（时间线 + 音频 + 屏幕）
  ├─ 任务 1.6: CLI 命令完善（start / analyze / sessions / replay）
  └─ 任务 1.7: 教学分析器（教案执行检查 + 预设问题回答检查）

Phase 2: 体验增强
  ├─ 升级 STT 为 SeedUplex（学生也可语音输出）
  ├─ 浏览器版 UI（从终端迁移到 Web）
  ├─ 屏幕理解（Vision API 分析教师演示内容）
  └─ 分析器增强（更多维度、历史对比）
```

---

## 11. 立即可以开始的行动

1. **申请火山引擎账号** → 开通 SeedASR 服务，获取 AppID/Token
2. **申请 Deepgram 账号** → 获取 $200 免费额度作为 STT fallback
3. **搭建项目脚手架** → Python + typer + rich + pyaudio
4. **编写示例教案** → 用上面的 YAML schema 写 1-2 份真实教案
5. **实现 Phase 0 的 3 个 Tech Spike** → 验证核心技术可行性
