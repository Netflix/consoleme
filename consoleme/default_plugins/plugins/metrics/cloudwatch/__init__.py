import concurrent.futures
import sys
from typing import Dict, Optional, Union

import boto3
import sentry_sdk

from consoleme.config import config
from consoleme.default_plugins.plugins.metrics.base_metric import Metric

cloudwatch = boto3.client(
    "cloudwatch", region_name=config.region, **config.get("boto3.client_kwargs", {})
)
log = config.get_logger()


def log_metric_error(future):
    try:
        future.result()
    except Exception as e:
        log.error(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Error sending metric",
                "error": str(e),
            },
            exc_info=True,
        )
        sentry_sdk.capture_exception()


class CloudWatchMetric(Metric):
    def __init__(self):
        self.namespace = config.get("metrics.cloudwatch.namespace", "ConsoleMe")
        self.executor = concurrent.futures.ThreadPoolExecutor(
            config.get("metrics.cloudwatch.max_threads", 10)
        )

    def send_cloudwatch_metric(self, metric_name, dimensions, unit, value):
        kwargs = {
            "Namespace": self.namespace,
            "MetricData": [
                {
                    "MetricName": metric_name,
                    "Dimensions": dimensions,
                    "Unit": unit,
                    "Value": value,
                },
            ],
        }
        future = self.executor.submit(cloudwatch.put_metric_data, **kwargs)
        future.add_done_callback(log_metric_error)

    def generate_dimensions(self, tags):
        dimensions = []
        if not tags:
            return dimensions
        for name, value in tags.items():
            dimensions.append({"Name": str(name), "Value": str(value)})
        return dimensions

    def count(self, metric_name, tags=None):
        dimensions = self.generate_dimensions(tags)

        self.send_cloudwatch_metric(metric_name, dimensions, "Count", 1)

    def gauge(self, metric_name, metric_value, tags=None):
        dimensions = self.generate_dimensions(tags)

        self.send_cloudwatch_metric(metric_name, dimensions, "Count", metric_value)

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        dimensions = self.generate_dimensions(tags)

        self.send_cloudwatch_metric(metric_name, dimensions, "Count/Second", 1)
