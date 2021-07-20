"""
Compute stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_applicationautoscaling as applicationautoscaling
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_elasticloadbalancingv2 as lb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import core as cdk

from consoleme_ecs_cdk.service.constants import (
    DOCKER_IMAGE,
    MAX_CAPACITY,
    MIN_CAPACITY,
    USE_PUBLIC_DOCKER_IMAGE,
)


class ComputeStack(cdk.NestedStack):
    """
    Compute stack for running ConsoleMe on ECS
    """

    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        vpc: ec2.Vpc,
        s3_bucket_name: str,
        certificate: acm.Certificate,
        consoleme_alb: lb.ApplicationLoadBalancer,
        consoleme_sg: ec2.SecurityGroup,
        task_role_arn: str,
        task_execution_role_arn: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ECS Task definition and volumes

        if USE_PUBLIC_DOCKER_IMAGE is True:
            docker_image = ecs.ContainerImage.from_registry(DOCKER_IMAGE)
        else:
            docker_image = ecs.ContainerImage.from_docker_image_asset(
                ecr_assets.DockerImageAsset(
                    self, "ConsoleMeCustomImage", directory="../"
                )
            )

        imported_task_role = iam.Role.from_role_arn(
            self, "ImportedTaskRole", role_arn=task_role_arn
        )

        imported_task_execution_role = iam.Role.from_role_arn(
            self, "ImportedTaskExecutionRole", role_arn=task_execution_role_arn
        )

        consoleme_ecs_task_definition = ecs.FargateTaskDefinition(
            self,
            "ConsoleMeTaskDefinition",
            cpu=2048,
            memory_limit_mib=4096,
            execution_role=imported_task_execution_role,
            task_role=imported_task_role,
        )

        # ECS Container definition, service, target group and ALB attachment

        consoleme_ecs_task_definition.add_container(
            "Container",
            image=docker_image,
            privileged=False,
            port_mappings=[
                ecs.PortMapping(
                    container_port=8081, host_port=8081, protocol=ecs.Protocol.TCP
                )
            ],
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ContainerLogs-",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "SETUPTOOLS_USE_DISTUTILS": "stdlib",
                "CONSOLEME_CONFIG_S3": "s3://" + s3_bucket_name + "/config.yaml",
                "EC2_REGION": self.region,
            },
            working_directory="/apps/consoleme",
            command=[
                "bash",
                "-c",
                "python scripts/retrieve_or_decode_configuration.py; python consoleme/__main__.py",
            ],
        )

        consoleme_ecs_task_definition.add_container(
            "CeleryContainer",
            image=docker_image,
            privileged=False,
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="CeleryContainerLogs-",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "SETUPTOOLS_USE_DISTUTILS": "stdlib",
                "CONSOLEME_CONFIG_S3": "s3://" + s3_bucket_name + "/config.yaml",
                "COLUMNS": "80",
                "EC2_REGION": self.region,
            },
            command=[
                "bash",
                "-c",
                "python scripts/retrieve_or_decode_configuration.py; python scripts/initialize_redis_oss.py; celery -A consoleme.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=8",
            ],
        )

        # ECS cluster

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        consoleme_imported_alb = (
            lb.ApplicationLoadBalancer.from_application_load_balancer_attributes(
                self,
                "ConsoleMeImportedALB",
                load_balancer_arn=consoleme_alb.load_balancer_arn,
                vpc=vpc,
                security_group_id=consoleme_sg.security_group_id,
                load_balancer_dns_name=consoleme_alb.load_balancer_dns_name,
            )
        )

        consoleme_ecs_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=consoleme_ecs_task_definition,
            load_balancer=consoleme_imported_alb,
            security_groups=[consoleme_sg],
            open_listener=False,
        )

        consoleme_ecs_service.target_group.configure_health_check(
            path="/", enabled=True, healthy_http_codes="200-302"
        )

        consoleme_ecs_service_scaling_target = applicationautoscaling.ScalableTarget(
            self,
            "AutoScalingGroup",
            max_capacity=MAX_CAPACITY,
            min_capacity=MIN_CAPACITY,
            resource_id="service/"
            + cluster.cluster_name
            + "/"
            + consoleme_ecs_service.service.service_name,
            scalable_dimension="ecs:service:DesiredCount",
            service_namespace=applicationautoscaling.ServiceNamespace.ECS,
            role=iam.Role(
                self,
                "AutoScaleRole",
                assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
                description="Role for ECS auto scaling group",
                managed_policies=[
                    iam.ManagedPolicy.from_managed_policy_arn(
                        self,
                        "AutoScalingManagedPolicy",
                        managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole",
                    )
                ],
            ),
        )

        applicationautoscaling.TargetTrackingScalingPolicy(
            self,
            "AutoScalingPolicy",
            scaling_target=consoleme_ecs_service_scaling_target,
            scale_in_cooldown=cdk.Duration.seconds(amount=10),
            scale_out_cooldown=cdk.Duration.seconds(amount=10),
            target_value=50,
            predefined_metric=applicationautoscaling.PredefinedMetric.ECS_SERVICE_AVERAGE_CPU_UTILIZATION,
        )

        consoleme_imported_alb.add_listener(
            "ConsoleMeALBListener",
            protocol=lb.ApplicationProtocol.HTTPS,
            port=443,
            certificates=[certificate],
            default_action=lb.ListenerAction.forward(
                target_groups=[consoleme_ecs_service.target_group]
            ),
        )
