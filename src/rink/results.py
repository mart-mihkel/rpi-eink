"""Helpers for turning failing async calls into ``Result`` values."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


def asafe[**P, T](
    fn: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[Result[T, Exception]]]:
    """Make an async function return a ``Result`` instead of raising."""

    @wraps(fn)
    async def wrapper(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Result[T, Exception]:
        try:
            return Success(await fn(*args, **kwargs))
        except Exception as exc:  # noqa: BLE001
            return Failure(exc)

    return wrapper
