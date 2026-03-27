"""内置：根据教学活动设计生成 PPT 大纲的固定提示词。"""

SYSTEM_PROMPT = """你是资深课程设计师与演示文稿策划师，擅长把教学活动设计转化为可直接用于制作幻灯片的结构化大纲。
要求：严格使用 Markdown 输出；语言与输入文档保持一致（多为中文）；不编造输入中未出现的教学目标或事实；不确定处标注「待确认」。
"""

PPT_OUTLINE_INSTRUCTIONS = """
根据下面的线上课程教学设计，生成适合给中国10-12岁小朋友的课程PPT大纲。

# 设计考虑
 - 原则上一个slide只有1个主题，但是如果有对比的内容，可以把对比的两个主题放在1页slide上
 - 上课时屏幕左侧是PPT，右侧是豆包大模型网页页面，我会同时使用这两种教学媒介。因此在PPT中不用保留太多操作细节
 - 配图使用原则
     + 如果页面上有"[图片]"占位符，不要使用配图 
     + 配图在ppt的右侧，在layout中说明
     + 配图一定要给出配图prompt
 - 休息页面不生成单独slides，最多页面不超过20个
 - 总结小黑板不要使用配图
 - 不要出现emoji
 - 不要使用文本高亮

# 内容
 - content-on-slide 是建议展示在slide的要点。关键重点可以加粗或者上颜色(HEX色号 #d62d3d)。在大纲中要保留原文中的"[图片]"占位符
   + 标题页使用一级标题（#），主题页使用二级标题（##）
 - lecture-context 逐字稿中和这一页相关的教学内容摘要，用于为AI生成slide提供context
 - layout：描述ppt的布局，如果有配图需要说明配图的位置（左侧或者右侧）
 - 首页“AI通识课·启航班 字号40，专题名称和课次名称字号45”
 - 每页都要有标题，标题以“##”表示

# 配图prompt
 - 如果图上出现人物/角色，请从下述三个角色中选择。图像提示词中的角色**必须使用完整角色提示词**，以保持人物形象一致
     + 海狸老师：cartoon beaver, eye glasses, dark blue suit and tie
     + AI机器人：atro bot from playstation
     + 小女孩: chinese girl look like Vanellope von Schweetz with double ponytails and pink dress
 - 图上如果要有文字，必须是中文
 - 风格要求：3D render, rich details, soft lighting
 

# 输出格式
为了便于下一步AI PPT制作，请以这样的格式输出，输出使用markdown
```
# Slide No.x
- content_on_slide:
- lecture_context:
- layout Slide标题页左图右文，其他页左文右图
- figure prompt: if necessary
---
# Slide No.x+1
```

# 教学设计
以下为教学设计原文

"""


def build_messages(design_markdown: str) -> list[dict[str, str]]:
    """构造 OpenRouter chat messages（拼接原文，避免 design 中含花括号时 format 报错）。"""
    body = design_markdown.strip()
    user_content = f"{PPT_OUTLINE_INSTRUCTIONS.strip()}\n{body}\n---\n"
    return [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_content.strip()},
    ]
