import json

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .db import Base


class DailyContent(Base):
    __tablename__ = "daily_content"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")  # pending / generated / failed

    title = Column(Text, default="")
    original_title = Column(Text, default="")
    pub_date = Column(String(20), default="")
    source_url = Column(Text, default="")
    source_name = Column(String(200), default="")
    category = Column(String(50), default="")

    summary_en = Column(Text, default="")
    summary_zh = Column(Text, default="")

    word = Column(String(100), default="")
    word_pos = Column(String(50), default="")
    word_phonetic = Column(String(100), default="")
    word_grade = Column(String(50), default="")

    definitions = Column(Text, default="[]")  # JSON list
    choices = Column(Text, default="[]")        # JSON list，2 道选词填空
    translation = Column(Text, default="{}")    # JSON {question, answer}

    image_dir = Column(String(255), default="")
    error = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def definitions_list(self):
        try:
            return json.loads(self.definitions or "[]")
        except json.JSONDecodeError:
            return []

    def choices_list(self):
        try:
            return json.loads(self.choices or "[]")
        except json.JSONDecodeError:
            return []

    def translation_dict(self):
        try:
            return json.loads(self.translation or "{}")
        except json.JSONDecodeError:
            return {}


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, default="")


class SlangContent(Base):
    __tablename__ = "slang_content"

    id = Column(Integer, primary_key=True)
    date = Column(String(10), unique=True, index=True, nullable=False)
    status = Column(String(20), default="pending")  # pending / generated / failed

    slang = Column(String(100), default="")
    phonetic = Column(String(100), default="")
    meaning_en = Column(Text, default="")
    meaning_zh = Column(Text, default="")
    usage = Column(Text, default="")

    examples = Column(Text, default="[]")   # JSON list {en, zh}
    scenarios = Column(Text, default="[]")  # JSON list {title, dialogue_en, dialogue_zh}

    source = Column(String(200), default="")
    source_url = Column(Text, default="")
    caption = Column(Text, default="")
    theme = Column(String(50), default="")

    image_dir = Column(String(255), default="")
    error = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def examples_list(self):
        try:
            return json.loads(self.examples or "[]")
        except json.JSONDecodeError:
            return []

    def scenarios_list(self):
        try:
            return json.loads(self.scenarios or "[]")
        except json.JSONDecodeError:
            return []
