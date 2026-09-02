import os
import tempfile

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="nes_test_")
os.environ["FONT_DIR"] = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "fonts"
)
os.environ["START_SCHEDULER"] = "0"
os.environ["SLANG_SOURCE"] = "auto"


@pytest.fixture(autouse=True)
def _init_db():
    from app.db import init_db

    init_db()
    yield
