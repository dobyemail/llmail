from dataclasses import dataclass
from typing import Any


@dataclass
class LogCtl:
    verbose: bool = False

    def info(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def debug(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def error(self, msg: str) -> None:
        print(msg)

    @staticmethod
    def short(obj: Any, limit: int = 20) -> str:
        try:
            s = str(obj)
        except Exception:
            try:
                s = repr(obj)
            except Exception:
                return '<unprintable>'
        return s if len(s) <= limit else s[:limit] + '...'
