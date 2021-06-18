from typing import Optional


class BaseVersionControl:
    async def clone(self, no_checkout=True, depth: Optional[int] = None):
        raise NotImplementedError

    async def cleanup(self):
        raise NotImplementedError
