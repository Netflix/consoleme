import asyncio
import concurrent.futures
import os

from consoleme.config import config
from consoleme.lib.singleton import Singleton


class GlobalThreadPool(metaclass=Singleton):
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(
            config.get("threading.global.max_threads", os.cpu_count())
        )

    def get_executor(self):
        return self.executor

    def execute_in_background_thread(self, func, args, kwargs, callback=None):
        future = self.executor.submit(func, *args, **kwargs)
        print("args: ", *args)
        print("kwargs: ", kwargs)
        print("func: ", func)
        if callback:
            future.add_done_callback(callback)
        return future

    def execute_in_background_thread_async(
        self, func, args=(), kwargs=(), callback=None
    ):
        loop = asyncio.get_event_loop()
        future = self.executor.submit(func, *args, **kwargs)
        print("args: ", *args)
        print("kwargs: ", kwargs)
        print("func: ", func)
        if callback:
            future.add_done_callback(callback)
        return future
