import threading
from typing import Dict, Optional, Union

import boto3

from consoleme.config import config
from consoleme_default_plugins.plugins.metrics.base_metric import Metric

cloudwatch = boto3.client("cloudwatch", region_name=config.region)


class CloudWatchMetric(Metric):
    def __init__(self):
        self.namespace = config.get("metrics.cloudwatch.namespace", "ConsoleMe")

    def send_cloudwatch_metric(self, metric_name, dimensions, unit, value):
        cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Dimensions": dimensions,
                    "Unit": unit,
                    "Value": value,
                },
            ],
        )

    def generate_dimensions(self, tags):
        dimensions = []
        if not tags:
            return dimensions
        for name, value in tags.items():
            dimensions.append({"Name": str(name), "Value": str(value)})
        return dimensions

    def count(self, metric_name, tags=None):
        dimensions = self.generate_dimensions(tags)

        threading.Timer(
            0, self.send_cloudwatch_metric, (metric_name, dimensions, "Count", 1)
        ).start()

    def gauge(self, metric_name, metric_value, tags=None):
        dimensions = self.generate_dimensions(tags)

        threading.Timer(
            0,
            self.send_cloudwatch_metric,
            (metric_name, dimensions, "Count", metric_value),
        ).start()

    def timer(
        self,
        metric_name: str,
        tags: Optional[Union[Dict[str, Union[str, bool]], Dict[str, str]]] = None,
    ) -> None:
        dimensions = self.generate_dimensions(tags)

        threading.Timer(
            0, self.send_cloudwatch_metric, (metric_name, dimensions, "Count/Second", 1)
        ).start()
