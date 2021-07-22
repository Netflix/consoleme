"""
VPC stack for running ConsoleMe on ECS
"""

import urllib.request

from aws_cdk import aws_ec2 as ec2
from aws_cdk import core as cdk


class VPCStack(cdk.NestedStack):
    """
    VPC stack for running ConsoleMe on ECS
    """

    def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # VPC and security groups

        vpc = ec2.Vpc(self, "Vpc", max_azs=2)

        consoleme_sg = ec2.SecurityGroup(
            self,
            "LBSG",
            vpc=vpc,
            description="ConsoleMe ECS service load balancer security group",
            allow_all_outbound=True,
        )

        # Open ingress to the deploying computer public IP

        my_ip_cidr = (
            urllib.request.urlopen("http://checkip.amazonaws.com")
            .read()
            .decode("utf-8")
            .strip()
            + "/32"
        )

        consoleme_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(cidr_ip=my_ip_cidr),
            connection=ec2.Port.tcp(port=443),
            description="Allow HTTPS traffic",
        )

        redis_sg = ec2.SecurityGroup(
            self,
            "ECSG",
            vpc=vpc,
            description="ConsoleMe Redis security group",
            allow_all_outbound=True,
        )

        redis_sg.connections.allow_from(
            consoleme_sg,
            port_range=ec2.Port.tcp(port=6379),
            description="Allow ingress from ConsoleMe containers",
        )

        self.vpc = vpc
        self.redis_sg = redis_sg
        self.consoleme_sg = consoleme_sg
