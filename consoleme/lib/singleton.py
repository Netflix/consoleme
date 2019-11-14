from typing import Any, Union


class Singleton(type):
    """Create singleton."""

    _instances = {}

    def __call__(cls, *args, **kwargs) -> Union[Any]:
        """Call Singleton."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
