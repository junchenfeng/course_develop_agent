---
description: Run course development workflows such as ppt-outline
argument-hint: <skill> [args...]
---

Use this command as the unified entry for course development workflows.

Supported skills:
- `ppt-outline <level> <unit> <lesson> [model]`

If `$1` is `ppt-outline`, do the following:
- Interpret `$2` as `level`
- Interpret `$3` as `unit`
- Interpret `$4` as `lesson`
- Interpret `$5` as the optional expected model label
- Use the `ppt-outline` skill to generate or refresh `ppt_outline.md`

Execution requirements:
- Normalize the lesson location to `course/<level>/<unit>/<lesson>/`.
- Read `activity_design.md` from that lesson directory.
- Use the `ppt-outline` skill rules to generate the PPT outline.
- Write the result to the same directory as `ppt_outline.md`.
- If the source file is missing or empty, stop and explain the problem instead of guessing.
- Do not call any Python CLI or external HTTP request manually.

If `$1` is unsupported, explain the currently supported skills and show the expected format:
- `/course-develop ppt-outline level_1 6 1`
