"""BE-062: 構造化ログユーティリティ"""
from __future__ import annotations
import logging
import json
from datetime import datetime, timezone


class StructuredLogger:
    def __init__(self, name: str):
        self.name = name

    def log(self, severity: str, message: str, **kwargs):
        entry = {
            "severity": severity,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": self.name,
            **kwargs,
        }
        print(json.dumps(entry, ensure_ascii=False))

    def info(self, msg: str, **kw): self.log("INFO", msg, **kw)
    def warning(self, msg: str, **kw): self.log("WARNING", msg, **kw)
    def error(self, msg: str, **kw): self.log("ERROR", msg, **kw)
    def critical(self, msg: str, **kw): self.log("CRITICAL", msg, **kw)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
