import asyncio
import os
from typing import List

from asgiref.sync import sync_to_async


async def bound_fetch(sem, fn, args, kwargs):
    # Getter function with semaphore.
    async with sem:
        return {
            "fn": fn,
            "args": args,
            "kwargs": kwargs,
            "result": await fn(*args, **kwargs),
        }


async def bound_fetch_sync(sem, fn, args, kwargs):
    # Getter function with semaphore.
    async with sem:
        return {
            "fn": fn,
            "args": args,
            "kwargs": kwargs,
            "result": await sync_to_async(fn)(*args, **kwargs),
        }


async def run_in_parallel(task_list: List, threads=os.cpu_count(), sync=True):
    async def run():
        sem = asyncio.Semaphore(threads)
        futures = []
        for task in task_list:
            if sync:
                futures.append(
                    asyncio.ensure_future(
                        bound_fetch_sync(
                            sem,
                            task.get("fn"),
                            task.get("args", ()),
                            task.get("kwargs", {}),
                        )
                    )
                )
            else:
                futures.append(
                    asyncio.ensure_future(
                        bound_fetch(
                            sem,
                            task.get("fn"),
                            task.get("args", ()),
                            task.get("kwargs", {}),
                        )
                    )
                )
        responses = asyncio.gather(*futures)
        return await responses

    return await run()
