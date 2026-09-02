import json

from openai import OpenAI

from ..config import settings
from .settings import get_setting

SYSTEM_PROMPT = """你是一名资深的初中英语教研老师，负责每天制作一张面向初中生的英语学习图文内容。
你的任务：从给定的新闻候选列表中挑选 1 条最适合初中生学习的新闻，并生成结构化学习内容。

【选题标准（非常重要）】
请优先选择最贴合初中生的新闻，具体标准：
1. 主题积极、健康、有教育意义，能引起初中生兴趣（如：科技新产品、校园与学习、环保、动物、体育比赛、健康生活、趣味科学等）。
2. 坚决避开：政治、战争、暴力、犯罪、灾难、明星八卦、成人话题、争议性话题。
3. 语言清晰简单，事情容易用简单英语讲清楚；过于专业、冷门或抽象的选题一律不选。
4. 优先科技、体育、财经类（在候选里做权衡，选最合适的 1 条即可）。

【内容要求】
1. 英文摘要控制在 3-4 个完整句子，使用初中阶段（约 800-1200 词汇量）的简单词汇和句型。
2. 中文翻译要准确、通顺、贴近原文。
3. 抽取 1 个初中核心词语（尽量是该新闻中出现或有强关联的实用词），给出 2-3 个核心释义。
4. 每个释义配 1 个英文例句和对应中文翻译，例句要简单、生活化。
5. 给出该核心词大致出现在几年级的课本（初中阶段按人教版等常见教材判断，如：七年级上册、八年级（初二）、九年级（初三）等）。
6. 出 2 道选词填空题（共 2 道）：
   - 第 1 题：给出一个句子，把当天核心词挖掉用 ______ 表示空，再提供 4 个单词选项（1 个是当天核心词，其余 3 个是词性相近的干扰词），让学生选出正确填入空格的词，正确答案是当天核心词。
   - 第 2 题：再出一道选词填空，4 个单词选项中要包含当天核心词（作为干扰项之一），但正确答案是另一个初中词汇，不是当天核心词。
   两道题的选项内容都不要带 A/B/C/D 字母前缀，只写单词本身。
7. 出 1 道翻译题：给一个简短的中文句子，让学生翻译成英文。翻译结果要使用初中核心词汇和简单句型，难度要低。
8. 所有英文句子都控制在初中可理解难度。

你必须严格只返回一个 JSON 对象，不要输出任何解释性文字、markdown 代码块或多余内容。
JSON 结构如下：
{
  "title": "新闻标题（可稍作精简）",
  "source_url": "原文链接",
  "source_name": "媒体名",
  "category": "科技/体育/财经",
  "summary_en": "3-4 个英文句子",
  "summary_zh": "对应的中文翻译",
  "word": "核心词语（英文单词）",
  "word_pos": "词性，如 n. / v. / adj.",
  "word_phonetic": "音标，如 /prəˈdjuːs/",
  "word_grade": "出现年级，如 八年级（初二）",
  "definitions": [
    {"meaning_en": "英文释义", "meaning_zh": "中文释义", "example_en": "英文例句", "example_zh": "例句翻译"}
  ],
  "choices": [
    {"question": "第1题句子（挖掉核心词，用 ______ 表示空）", "options": ["正确单词", "干扰词1", "干扰词2", "干扰词3"], "answer": "正确选项字母，如 B"},
    {"question": "第2题句子（用 ______ 表示空）", "options": ["干扰词含核心词", "干扰词", "正确单词", "干扰词"], "answer": "正确选项字母，如 C"}
  ],
  "translation": {"question": "需要翻译成英文的中文句子", "answer": "对应的英文翻译"}
}
"""


def _client() -> OpenAI:
    key = get_setting("deepseek_api_key") or settings.deepseek_api_key
    if not key:
        raise RuntimeError("DeepSeek API Key 未配置，请在后台设置中填写")
    return OpenAI(api_key=key, base_url=settings.deepseek_base_url)


def _call_llm(system_prompt: str, user_msg: str) -> dict:
    client = _client()
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        timeout=120,
    )

    content = resp.choices[0].message.content or ""
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)


def generate_content(articles: list[dict]) -> dict:
    candidates = json.dumps(articles, ensure_ascii=False)
    user = (
        "以下是今日新闻候选列表（JSON 数组，字段含 title/description/url/source/category/category_label）：\n\n"
        f"{candidates}\n\n"
        "请按要求挑选 1 条并生成学习内容，严格返回 JSON。"
    )
    return _call_llm(SYSTEM_PROMPT, user)


SLANG_SYSTEM_PROMPT = """你是一名精通地道英语口语的英语老师，面向成年人分享每日地道俚语表达。
你的任务：从给定的候选内容中挑选 1 个最有学习价值的地道俚语表达，并生成学习内容。

要求：
1. 候选内容可能来自热门帖子（标题/正文），也可能来自俚语词典词条（词条正文可能较粗糙，需要你提炼润色）。
2. 俚语要地道、常用、适合成年人日常交流，避免生僻或过时的表达。
3. 坚决避开粗俗、冒犯、歧视性、涉及敏感话题的表达；只选择适合公开分享学习的俚语。
4. 给出英文释义和中文释义，中文要准确自然。
5. 给出 2-3 条简短用法说明（口语用法、语境、语气，用换行或分号分隔）。
6. 给出 2-3 个英文例句及中文翻译，例句贴近日常生活。
7. 给出 2-3 个使用场景，每个场景配一段简短中英对话（2-4 句）。
8. 内容面向成年人，例子可以更贴近工作、生活、社交等成人场景。
9. 生成一条社交平台发布文案 caption，严格按以下模板填写（把【】换成具体内容，保留其余文字和引号）：
你是否有过【具体经历/场景】的经历，这样的经历向你的外国朋友要怎么描述呢？不要再说【传统表达（被这个俚语替代的常规说法）】了，今天我们的slang "【俚语】"帮你的外国朋友秒懂！

重要：输出的 slang 必须从本次提供的候选内容中挑选/提炼，绝不要输出候选列表里不存在的表达，也不要使用本提示文字里出现过的任何例子词。

你必须严格只返回一个 JSON 对象，不要输出任何解释性文字、markdown 代码块或多余内容。
JSON 结构如下：
{
  "slang": "俚语表达",
  "phonetic": "该俚语的标准音标",
  "meaning_en": "英文释义",
  "meaning_zh": "中文释义",
  "usage": "用法说明",
  "examples": [{"en": "英文例句", "zh": "中文翻译"}],
  "scenarios": [
    {"title": "场景标题", "dialogue_en": "A: ...\\nB: ...", "dialogue_zh": "A：...\\nB：..."}
  ],
  "source": "来源，如 Reddit r/AskReddit 或 Urban Dictionary",
  "source_url": "来源链接",
  "caption": "按模板生成的发布文案"
}
"""


def generate_slang(posts: list[dict], strict: bool = False) -> dict:
    candidates = json.dumps(posts, ensure_ascii=False)
    strict_hint = (
        "\n注意：上次输出的表达不在候选列表中，本次必须严格从候选里挑选一个真实出现的俚语/表达。"
        if strict
        else ""
    )
    user = (
        "以下是今日候选内容列表（JSON 数组，字段含 title/selftext/source/url/score）：\n\n"
        f"{candidates}\n\n"
        f"请从中挑选/提炼 1 个最值得学习、适合公开分享的地道俚语并生成内容，严格返回 JSON。{strict_hint}"
    )
    return _call_llm(SLANG_SYSTEM_PROMPT, user)
