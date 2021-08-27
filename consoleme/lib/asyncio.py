import asyncio
import os
from asyncio import Task
from typing import List

# TODO: Install nest_asyncio in requirements
import nest_asyncio
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


def asyncio_run(future, as_task=True):
    """
    A better implementation of `asyncio.run`.

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_to_task(future, as_task, loop))
    else:
        nest_asyncio.apply(loop)
        return asyncio.run(_to_task(future, as_task, loop))


def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, Task):
        return future
    return loop.create_task(future)
