"""Custom exception types for the Backsberger Open API."""

from __future__ import annotations


class AppError(Exception):
    """Application-level error with an HTTP status code and a machine-readable code."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


def not_found(resource: str, resource_id: int | str) -> AppError:
    return AppError(
        status_code=404,
        detail=f"{resource} {resource_id} not found",
        code=f"{resource.lower().replace(' ', '_')}_not_found",
    )


def conflict(detail: str, code: str) -> AppError:
    return AppError(status_code=409, detail=detail, code=code)


def bad_request(detail: str, code: str) -> AppError:
    return AppError(status_code=400, detail=detail, code=code)
