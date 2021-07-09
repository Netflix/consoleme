"""
Cache stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticache as ec
from aws_cdk import core as cdk


class CacheStack(cdk.NestedStack):
    """
    Cache stack for running ConsoleMe on ECS
    """

    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        redis_sg: ec2.SecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Redis node

        subnet_ids = []
        for subnet in vpc.private_subnets:
            subnet_ids.append(subnet.subnet_id)

        redis_subnet_group = ec.CfnSubnetGroup(
            self,
            "RedisSubnetGroup",
            cache_subnet_group_name="redis-subnet-group",
            description="Subnet group for Redis Cluster",
            subnet_ids=subnet_ids,
        )

        redis = ec.CfnCacheCluster(
            self,
            "RedisCluster",
            cache_node_type="cache.t3.micro",
            engine="redis",
            engine_version="6.x",
            num_cache_nodes=1,
            auto_minor_version_upgrade=True,
            cache_subnet_group_name=redis_subnet_group.ref,
            vpc_security_group_ids=[redis_sg.security_group_id],
        )

        self.redis = redis
