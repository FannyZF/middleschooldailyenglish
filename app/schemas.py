import re
from typing import List

from pydantic import BaseModel, field_validator


class Definition(BaseModel):
    meaning_en: str = ""
    meaning_zh: str = ""
    example_en: str = ""
    example_zh: str = ""


_PREFIX_RE = re.compile(r"^\s*[A-Da-d]\s*[\.\、\)）:：]\s*")


class ChoiceQuestion(BaseModel):
    question: str = ""
    options: List[str] = []  # 4 个选项（不含 A/B/C/D 字母）
    answer: str = ""  # 正确选项，如 "B"

    @field_validator("options")
    @classmethod
    def _clean_options(cls, v: List[str]) -> List[str]:
        return [_PREFIX_RE.sub("", o).strip() for o in v]

    @field_validator("answer")
    @classmethod
    def _clean_answer(cls, v: str) -> str:
        v = (v or "").strip()
        m = re.match(r"^[A-Da-d]", v)
        return m.group(0).upper() if m else v


class TranslationQuestion(BaseModel):
    question: str = ""  # 中文句子
    answer: str = ""  # 英文翻译


class Content(BaseModel):
    title: str = ""
    source_url: str = ""
    source_name: str = ""
    category: str = ""
    original_title: str = ""  # RSS 原文标题
    pub_date: str = ""  # 新闻发布日期 YYYY-MM-DD
    summary_en: str = ""
    summary_zh: str = ""
    word: str = ""
    word_pos: str = ""
    word_phonetic: str = ""
    word_grade: str = ""  # 出现的年级，如 "八年级（初二）"
    definitions: List[Definition] = []
    choices: List[ChoiceQuestion] = []  # 2 道选词填空
    translation: TranslationQuestion = TranslationQuestion()


class SlangExample(BaseModel):
    en: str = ""
    zh: str = ""


class SlangScenario(BaseModel):
    title: str = ""
    dialogue_en: str = ""
    dialogue_zh: str = ""


class SlangContent(BaseModel):
    slang: str = ""
    phonetic: str = ""
    meaning_en: str = ""
    meaning_zh: str = ""
    usage: str = ""
    examples: List[SlangExample] = []
    scenarios: List[SlangScenario] = []
    source: str = ""
    source_url: str = ""
    caption: str = ""  # 社交平台发布文案
    hook: str = ""  # 封面钩子句（一句话真实场景）
    theme: str = ""  # 主题：职场/学生/日常生活/社交/网络热词/情感
