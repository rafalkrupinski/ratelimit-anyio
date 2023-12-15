import asyncio
from collections.abc import Callable, Iterable
import dataclasses as dc
import datetime as dt
import logging
from typing import Any
import typing as ty

import anyio

logger = logging.getLogger(__name__)


@dc.dataclass(frozen=True, slots=True)
class RateLimit:
    interval: dt.timedelta
    limit: int


@dc.dataclass(slots=True)
class RemainingLimit:
    value: int
    last_reset: float


class CallRateError(Exception):
    def __init__(self, wait_time: float):
        super().__init__('Rate limit exceeded', wait_time)
        self.wait_time = wait_time


Wrapped = ty.TypeVar('Wrapped', bound=Callable)


class RateLimiter:
    def __init__(
            self,
            limits: Iterable[RateLimit],
    ):
        self._limits = sorted(limits, key=lambda limit: limit.interval, reverse=True)
        now = anyio.current_time()
        self._remaining = {limit.interval: RemainingLimit(limit.limit, now) for limit in self._limits}

    def __call__(self, cost: int = 1) -> Wrapped:
        def decorator(func: Wrapped | None = None):
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                self._before_call(cost)
                return await func(*args, **kwargs)

            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                self._before_call(cost)
                return func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def _before_call(self, cost: int) -> None:
        now = anyio.current_time()
        logger.debug('Now: %f', now)
        self._maybe_reset_remaining(now)
        logger.debug("%s, %d", self._remaining.values(), cost)
        min_period, min_remaining = min(self._remaining.items(), key=lambda item: item[1].value)

        if min_remaining.value < cost:
            raise CallRateError(min_remaining.last_reset + min_period.total_seconds() - now)

        for remaining in self._remaining.values():
            remaining.value -= cost
            assert remaining.value >= 0

    def _maybe_reset_remaining(self, now: float) -> None:
        for limit in self._limits:
            remaining = self._remaining[limit.interval]
            if now >= remaining.last_reset + limit.interval.total_seconds():
                logger.debug('Reset %s: %d', limit.interval, limit.limit)
                remaining.value = limit.limit
                remaining.last_reset = now

    def __repr__(self) -> str:
        return f"[RateLimiter {', '.join(f'{limit.interval}: {self._remaining[limit.interval].value}/{limit.limit} {self._remaining[limit.interval].last_reset}' for limit in self._limits)}]"


async def sleep_and_retry(fn: Wrapped, count=1, *args, **kwargs) -> Any:
    async def run()->bool:
        try:
            await fn(*args, **kwargs)
            return True
        except CallRateError as e:
            await anyio.sleep(e.wait_time)
            return False

    if count:
        for _ in range(count):
            if await run():
                break
    else:
        while not run():
            pass
