from __future__ import annotations

import logging


class _OpencodeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        stamp = self.formatTime(record, "%H:%M:%S")
        message = record.getMessage().encode("ascii", errors="replace").decode("ascii")
        if record.name == "pipeline":
            return f"[{stamp}] {message}"
        return f"[{stamp}] [{record.name}] {message}"


def get_logger(name: str) -> logging.Logger:
    root = logging.getLogger("prospecting")
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_OpencodeFormatter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False

    logger = root.getChild(name)
    logger.propagate = True
    return logger
