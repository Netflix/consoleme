from typing import List

import boto3
import ujson as json
from consoleme_internal.plugins.group_mapping.group_mapping import Spinnaker

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()
spinnaker = Spinnaker()

client = boto3.client("config")


def query(query: str) -> List:
    resources = []
    configuration_aggregator_name: str = config.get(
        "aws_config.configuration_aggregator.name"
    )
    if not configuration_aggregator_name:
        raise MissingConfigurationValue("Invalid configuration for aws_config")
    response = client.select_aggregate_resource_config(
        Expression=query,
        ConfigurationAggregatorName=configuration_aggregator_name,
        Limit=100,
    )
    for r in response.get("Results", []):
        resources.append(json.loads(r))
    while response.get("NextToken"):
        response = client.select_aggregate_resource_config(
            Expression=query,
            ConfigurationAggregatorName=configuration_aggregator_name,
            Limit=100,
            NextToken=response["NextToken"],
        )
        for r in response.get("Results", []):
            resources.append(json.loads(r))
    return resources
