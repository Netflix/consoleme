"""
Application load balancer stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as lb
from aws_cdk import core as cdk


class ALBStack(cdk.NestedStack):
    """
    Application load balancer stack for running ConsoleMe on ECS
    """

    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        consoleme_sg: ec2.SecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ECS Load Balancer

        consoleme_alb = lb.ApplicationLoadBalancer(
            self,
            "ConsoleMeALB",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            internet_facing=True,
        )

        consoleme_alb.add_security_group(
            ec2.SecurityGroup.from_security_group_id(
                self,
                "ImportedConsoleMeLBSG",
                security_group_id=consoleme_sg.security_group_id,
                mutable=False,
            )
        )

        self.consoleme_alb = consoleme_alb
