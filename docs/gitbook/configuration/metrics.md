# Metrics

ConsoleMe supports CloudWatch metrics, and other custom Metrics plugins should you wish to write one.

To enable CloudWatch Metrics, set this configuration entry:

```text
metrics
  metrics_plugin: consoleme.default_plugins.plugins.metrics.cloudwatch.CloudWatchMetric
```

To set up your own Metrics provider, create a child class that inherits the [Metric](https://github.com/Netflix/consoleme/blob/master/consoleme/default_plugins/plugins/metrics/base_metric.py#L4) class. Override the methods in the Metric class to emit metrics in your preferred way, make your code available in ConsoleMe's Python environment, and configure your `metrics.metrics_plugin` configuration entry to point to your new class.

If possible, please submit any generic metrics solutions to the open source codebase.

