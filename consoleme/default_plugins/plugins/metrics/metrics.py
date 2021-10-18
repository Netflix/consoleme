from consoleme.config import config
from consoleme.lib.plugins import import_class_by_name

desired_metric_plugin = config.get(
    "metrics.metrics_plugin",
    "consoleme.default_plugins.plugins.metrics.default_metrics.DefaultMetric",
)

try:
    Metric = import_class_by_name(desired_metric_plugin)
except ImportError:
    raise


def init():
    """Initialize metrics plugin."""
    return Metric
