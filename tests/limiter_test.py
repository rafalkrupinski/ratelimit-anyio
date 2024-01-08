from datetime import timedelta
import logging

import anyio
import pytest

from ratelimit_anyio import CallRateError, RateLimit, RateLimiter, sleep_and_retry

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_acquire():
    limiter = RateLimiter((
        RateLimit(timedelta(seconds=1), 1),
        RateLimit(timedelta(seconds=10), 5),
    ))

    @limiter()
    async def fn():
        logger.info('call')

    logger.info(limiter)

    await fn()
    logger.info(limiter)

    async with anyio.create_task_group() as tg:
        for _ in range(4):
            tg.start_soon(sleep_and_retry, fn, 4)

    logger.info(limiter)

    with pytest.raises(CallRateError):
        await fn()
    logger.info(limiter)

    await sleep_and_retry(fn)
    logger.info(limiter)


@pytest.mark.asyncio
async def test_sleep_and_retry_result():
    limiter = RateLimiter((
        RateLimit(timedelta(seconds=1), 1),
        RateLimit(timedelta(seconds=10), 5),
    ))

    @limiter()
    async def fn()->str:
        return 'hi'

    greeting = await sleep_and_retry(fn)
    assert greeting == 'hi'
