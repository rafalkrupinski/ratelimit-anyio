This packages introduces a function decorator preventing a functions from being called more often than allowed.
This should prevent API providers from banning your applications by conforming to their rate limits.

It's similar to [ratelimit](https://pypi.org/project/ratelimit/) with the following differences:

- also handles async functions
- accepts multiple limits (burst mode)
- allows applying rate limit to many functions
- allows assigning a cost
- sleep_and_retry utility is a function and accepts a limit of retries (1 by default)

Thanks to [anyio](https://pypi.org/project/anyio/) it works under asyncio and trio event loops.

## Usage

```python
from datetime import timedelta
from ratelimit_anyio import *

limiter = RateLimiter((
    RateLimit(timedelta(seconds=10), 10),
    RateLimit(timedelta(minutes=10), 100),
))

@limiter(cost=1)
async def function():
    # Simulate a remote call
    import asyncio
    await asyncio.sleep(3)
```

This function can be called up to 100 times within 10 minutes, and 10 times within any 10 seconds (burst mode).
You can also declare functions cost (1 by default) which is useful when applying to more than one function, and they use the quota by different values