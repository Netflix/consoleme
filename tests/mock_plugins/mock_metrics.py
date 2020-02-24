from typing import Dict, Optional, Union


class MockDefaultMetrics:
    def count(self, metric_name, tags=None):
        pass

    def gauge(self, metric_name, metric_value, tags=None):
        pass

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        pass


def init():
    """Initialize metrics plugin."""
    return MockDefaultMetrics()
