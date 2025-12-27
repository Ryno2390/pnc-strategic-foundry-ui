from typing import Any, Optional
from enum import Enum

class ErrorCodes:
    SUCCESS = 0
    INVALID_PARAMETER = 1001
    NOT_FOUND = 1002
    INTERNAL_ERROR = 5000

class APIResponse:
    @staticmethod
    def success(data: Any = None, message: str = "success") -> dict:
        return {
            "status": True,
            "code": ErrorCodes.SUCCESS,
            "message": message,
            "data": data
        }

    @staticmethod
    def error(message: str, code: int = ErrorCodes.INTERNAL_ERROR, data: Any = None) -> dict:
        return {
            "status": False,
            "code": code,
            "message": message,
            "data": data
        }

class APIError(Exception):
    def __init__(
        self, message: str, code: int = ErrorCodes.INTERNAL_ERROR, data: Any = None
    ):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)
