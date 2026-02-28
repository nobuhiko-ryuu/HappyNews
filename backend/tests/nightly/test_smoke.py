"""Nightly smoke tests - requires EXTERNAL_MODE=real and real credentials"""
from __future__ import annotations
import os
import pytest

# ナイトリー以外はスキップ
pytestmark = pytest.mark.skipif(
    os.getenv("EXTERNAL_MODE") != "real",
    reason="Nightly smoke requires EXTERNAL_MODE=real",
)


def test_smoke_placeholder():
    """Placeholder - real smoke tests require live credentials"""
    assert os.getenv("EXTERNAL_MODE") == "real"
