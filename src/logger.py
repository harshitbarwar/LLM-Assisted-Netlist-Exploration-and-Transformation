from __future__ import annotations

from pathlib import Path
from typing import Optional


class ResponseLogger:
    def __init__(self, case_name: Optional[str]) -> None:
        self.case_name = case_name

    def log(self, text: str) -> None:
        if not self.case_name:
            return
        path = Path(f"{self.case_name}.log")
        with path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
