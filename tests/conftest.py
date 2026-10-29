import pytest
import os
import uuid
from database.db import init_db

@pytest.fixture(autouse=True)
def ensure_db():
    init_db()

@pytest.fixture
def unique_code():
    return f"CLS-{uuid.uuid4().hex[:6].upper()}"
