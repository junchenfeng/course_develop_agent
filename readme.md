# 课程资料目录（数据架构）

所有课程设计文件放在仓库根目录下的 **`course/`** 中。

## 目录含义

| 层级 | 说明 |
|------|------|
| **`course/level_1/`** | 基础启航班 |
| **`course/level_2/`** | 进阶智造营 |
| **`unit_x/`** | 第 `x` 单元，例如 `unit_1`、`unit_6` |
| **`lesson_1/`、`lesson_2/`、`lesson_3/`** | 该单元下第 1～3 课 |

## 课次内文件（固定文件名）

每个课次对应一个目录，目录内包含两个 Markdown 文件：

| 文件 | 说明 |
|------|------|
| **`activity_design.md`** | 教学活动设计（编写与维护的源稿） |
| **`ppt_outline.md`** | PPT 大纲（由助手根据 `activity_design.md` 生成，写入同一路径） |

## 目录示例

```text
course/
  level_1/
    unit_6/
      lesson_1/
        activity_design.md
        ppt_outline.md
      lesson_2/
        activity_design.md
        ppt_outline.md
      lesson_3/
        activity_design.md
        ppt_outline.md
  level_2/
    unit_1/
      lesson_1/
        activity_design.md
        ppt_outline.md
      ...
```

在项目根目录执行（需已配置运行环境与 API 密钥）：

```bash
python -m src.cli --level level_1 --unit 6 --lesson 1
```

将在 `course/level_1/unit_6/lesson_1/` 下生成或覆盖 `ppt_outline.md`。
