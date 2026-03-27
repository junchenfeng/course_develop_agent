# 课程资料目录（Claude Code 原生版）

本仓库已经去掉 Python 生成中间层，`ppt_outline.md` 现在由 Claude Code 原生命令直接生成。

## 课程目录

所有课程设计文件放在仓库根目录下的 `course/` 中。

| 层级 | 说明 |
|------|------|
| `course/level_1/` | 基础启航班 |
| `course/level_2/` | 进阶智造营 |
| `unit_x/` | 第 `x` 单元，例如 `unit_1`、`unit_6` |
| `lesson_1/`、`lesson_2/`、`lesson_3/` | 该单元下第 1～3 课 |

每个课次目录包含：

| 文件 | 说明 |
|------|------|
| `activity_design.md` | 教学活动设计源稿 |
| `ppt_outline.md` | Claude Code 根据 `activity_design.md` 直接生成的 PPT 大纲 |

## 目录示例

```text
course/
  level_1/
    unit_6/
      lesson_1/
        activity_design.md
        ppt_outline.md
```

## Claude Code 主入口

项目级 Claude Code 资产：
- `.claude/commands/course-develop.md`
- `.claude/skills/ppt-outline/SKILL.md`

当前采用“一个 command 挂多个 skill”的结构：
- 统一命令：`/course-develop`
- 当前已接入 skill：`ppt-outline`

在仓库根目录启动 Claude Code 后，使用：

```text
/course-develop ppt-outline level_1 6 1
```

也可以显式传入一个期望模型标签：

```text
/course-develop ppt-outline level_1 6 1 xiaomi/mimo-v2-pro
```

说明：
- 第 1 个参数是 skill 名。
- `ppt-outline` 的第 4 个业务参数只用于说明你期望使用的模型。
- 实际执行使用当前 Claude Code 会话通过 `/model` 选中的模型。
- 命令会直接读取对应 lesson 下的 `activity_design.md`，并写回同目录的 `ppt_outline.md`。

## OpenRouter 模型建议

建议在 Claude Code 中将模型映射到 OpenRouter，例如：
- Default / Sonnet: `xiaomi/mimo-v2-pro`
- Haiku: `xiaomi/mimo-v2-omni`
- Opus: `anthropic/claude-opus-4.6`

如果要确认当前会话实际走的是哪个入口与提供商，可在 Claude Code 中执行：

```text
/status
/model
```

## 配置说明

Claude Code 原生模式不会读取项目 `.env` 作为运行时配置源。OpenRouter 相关变量应配置在：
- shell profile，例如 `~/.zshrc`
- 或项目级 `.claude/settings.local.json`

`.env.example` 在本仓库中仅作为环境变量命名参考。
