from typing import Dict, Optional, Union

from consoleme.config import config
from consoleme_default_plugins.plugins.metrics.cloudwatch import CloudWatchMetric


class Metric:
    def count(self, metric_name, tags=None):
        # TODO(ccastrapel): Having Cloudwatch, Graphite, or other configurtable default metric sources here would be a
        # good idea.
        pass

    def gauge(self, metric_name, metric_value, tags=None):
        pass

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        pass


if config.get("metrics.metrics_provider") == "cloudwatch":
    Metric = CloudWatchMetric  # noqa: F811


def init():
    """Initialize metrics plugin."""
    return Metric()
