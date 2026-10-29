"""共享错误类型：带退出码的业务异常。"""

from __future__ import annotations

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_CDP_UNAVAILABLE = 3


class SsstoolError(Exception):
    """可预期的业务失败：message 直接展示给用户，code 作为进程退出码。"""

    def __init__(self, message: str, code: int = EXIT_FAILURE) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
