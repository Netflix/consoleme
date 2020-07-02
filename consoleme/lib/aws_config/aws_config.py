from typing import List, Optional

import boto3
import ujson as json
from cloudaux.aws.sts import boto3_cached_conn

from consoleme.config import config
from consoleme.exceptions.exceptions import MissingConfigurationValue
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger()
stats = get_plugin_by_name(config.get("plugins.metrics"))()


def query(
    query: str, use_aggregator: bool = True, account_id: Optional[str] = None
) -> List:
    resources = []
    if use_aggregator:
        config_client = boto3.client("config", region_name=config.region)
        configuration_aggregator_name: str = config.get(
            "aws_config.configuration_aggregator.name"
        ).format(region=config.region)
        if not configuration_aggregator_name:
            raise MissingConfigurationValue("Invalid configuration for aws_config")
        response = config_client.select_aggregate_resource_config(
            Expression=query,
            ConfigurationAggregatorName=configuration_aggregator_name,
            Limit=100,
        )
        for r in response.get("Results", []):
            resources.append(json.loads(r))
        while response.get("NextToken"):
            response = config_client.select_aggregate_resource_config(
                Expression=query,
                ConfigurationAggregatorName=configuration_aggregator_name,
                Limit=100,
                NextToken=response["NextToken"],
            )
            for r in response.get("Results", []):
                resources.append(json.loads(r))
        return resources
    else:  # Don't use Config aggregator and instead query all the regions on an account
        session = boto3.Session()
        available_regions = session.get_available_regions("config")
        excluded_regions = config.get("api_protect.exclude_regions", [])
        regions = [x for x in available_regions if x not in excluded_regions]
        for region in regions:
            config_client = boto3_cached_conn(
                "config",
                account_number=account_id,
                assume_role=config.get("policies.role_name"),
                region=region,
            )
            response = config_client.select_resource_config(Expression=query, Limit=100)
            for r in response.get("Results", []):
                resources.append(json.loads(r))
            # Query Config for a specific account in all regions we care about
            while response.get("NextToken"):
                response = config_client.select_resource_config(
                    Expression=query, Limit=100, NextToken=response["NextToken"]
                )
                for r in response.get("Results", []):
                    resources.append(json.loads(r))
        return resources
