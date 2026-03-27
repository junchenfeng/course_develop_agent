---
name: ppt-outline
description: Generate or refresh `ppt_outline.md` from `course/<level>/<unit>/<lesson>/activity_design.md` using Claude Code native file reading and writing. Use when the user asks to produce lesson PPT outlines with level, unit, and lesson inputs.
---

# PPT Outline

## Purpose
Use this skill to generate a lesson PPT outline directly inside Claude Code without any Python runtime.

## Inputs
- `level`: `level_1` or `level_2` and also accepts `1` or `2`
- `unit`: accepts `6` or `unit_6`
- `lesson`: accepts `1` or `lesson_1`
- `model`: optional expected model label; actual execution uses the current Claude Code session model selected by `/model`

## Workflow
1. Normalize inputs to `level_x/unit_x/lesson_x`.
2. Read `course/<level>/<unit>/<lesson>/activity_design.md`.
3. Stop and report clearly if the file is missing or empty.
4. Generate the outline in Markdown only.
5. Write the result to `course/<level>/<unit>/<lesson>/ppt_outline.md`.
6. Verify the output keeps the required slide structure and formatting rules.

## System Prompt
You are a senior curriculum designer and presentation planner who converts lesson activity designs into structured PPT outlines that can be used directly for slide production.

Requirements:
- Output must be Markdown only.
- Keep the same language as the input document, usually Chinese.
- Do not invent facts or teaching goals that are not present in the input.
- Mark uncertain details as `待确认`.

## Generation Rules
Generate a PPT outline for an online class aimed at Chinese children aged 10-12.

### Design Rules
- In principle, one slide should contain one theme, but comparison content may place two related themes on one slide.
- During teaching, the PPT is shown on the left side of the screen and the Doubao model page is shown on the right side, so the PPT should not retain too many operational details.
- Image rules:
  - If the page already contains the placeholder `[图片]`, do not add a separate image suggestion.
  - If an image is needed, place it on the right side in the layout description.
  - Every added image must include a figure prompt.
- Do not generate a separate break slide.
- Use no more than 20 slides.
- Do not use images on the summary blackboard slide.
- Do not use emoji.
- Do not use text highlighting.

### Content Rules
- `content_on_slide` contains the visible points for the slide. Important points may use bold or the HEX color `#d62d3d`.
- Preserve any original `[图片]` placeholder from the source text.
- The title slide uses `#`, other content slides use `##`.
- `lecture_context` is a concise teaching summary related to the slide and is used as context for future AI slide production.
- `layout` describes the slide layout and must mention image position when an image is used.
- The first page should contain `AI通识课·启航班` with font size 40, and the topic name plus lesson name with font size 45.
- Every page must have a title introduced by `##`, except the title slide which uses `#`.

### Figure Prompt Rules
- If a character appears, use one of the following full prompts exactly:
  - `cartoon beaver, eye glasses, dark blue suit and tie`
  - `atro bot from playstation`
  - `chinese girl look like Vanellope von Schweetz with double ponytails and pink dress`
- If text appears in the image, it must be Chinese.
- Style requirement: `3D render, rich details, soft lighting`

## Output Format
Use exactly this Markdown pattern:

```markdown
# Slide No.x
- content_on_slide:
- lecture_context:
- layout: Slide标题页左图右文，其他页左文右图
- figure prompt: if necessary
---
# Slide No.x+1
```

## Execution Notes
- Use the current Claude Code session model. If the user passes a `model` argument, treat it as the expected model name and mention any mismatch if it is obvious from the conversation.
- Do not shell out to `python`, `curl`, or any external generator.
- Write the final file directly with Claude Code file tools.
