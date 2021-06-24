"""
Compute stack for running ConsoleMe on ECS
"""

import yaml

from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as lb,
    aws_logs as logs,
    aws_iam as iam,
    aws_certificatemanager as acm,
    aws_applicationautoscaling as applicationautoscaling,
    core as cdk
)

from constants import CONTAINER_IMAGE


class ComputeStack(cdk.NestedStack):
    """
    Compute stack for running ConsoleMe on ECS
    """

    def __init__(self, scope: cdk.Construct, id: str,
                 vpc: ec2.Vpc, s3_bucket_name: str, certificate: acm.Certificate,
                 consoleme_alb: lb.ApplicationLoadBalancer, consoleme_sg: ec2.SecurityGroup,
                 task_role_arn: str, task_execution_role_arn: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        config_yaml = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)

        # ECS Task definition and volumes

        imported_task_role = iam.Role.from_role_arn(
            self,
            'ImportedTaskRole',
            role_arn=task_role_arn
        )

        imported_task_execution_role = iam.Role.from_role_arn(
            self,
            'ImportedTaskExecutionRole',
            role_arn=task_execution_role_arn
        )

        consoleme_ecs_task_definition = ecs.FargateTaskDefinition(
            self,
            'ConsolemeTaskDefinition',
            cpu=2048,
            memory_limit_mib=4096,
            execution_role=imported_task_execution_role,
            task_role=imported_task_role
        )

        # ECS Container definition, service, target group and ALB attachment

        consoleme_ecs_task_definition.add_container(
            'Container',
            image=ecs.ContainerImage.from_registry(CONTAINER_IMAGE),
            privileged=False,
            port_mappings=[
                ecs.PortMapping(
                    container_port=8081,
                    host_port=8081,
                    protocol=ecs.Protocol.TCP
                )
            ],
            logging=ecs.LogDriver.aws_logs(
                stream_prefix='ContainerLogs-',
                log_retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'SETUPTOOLS_USE_DISTUTILS': 'stdlib',
                'CONSOLEME_CONFIG_S3': 's3://' + s3_bucket_name + '/config.yaml'
            },
            working_directory='/apps/consoleme',
            command=[
                "bash", "-c", "python scripts/retrieve_or_decode_configuration.py; python consoleme/__main__.py"]
        )

        consoleme_ecs_task_definition.add_container(
            'CeleryContainer',
            image=ecs.ContainerImage.from_registry(CONTAINER_IMAGE),
            privileged=False,
            logging=ecs.LogDriver.aws_logs(
                stream_prefix='CeleryContainerLogs-',
                log_retention=logs.RetentionDays.ONE_WEEK
            ),
            environment={
                'SETUPTOOLS_USE_DISTUTILS': 'stdlib',
                'CONSOLEME_CONFIG_S3': 's3://' + s3_bucket_name + '/config.yaml',
                'COLUMNS': '80'
            },
            command=["bash", "-c",
                     "python scripts/retrieve_or_decode_configuration.py; python scripts/initialize_redis_oss.py; celery -A consoleme.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=8"]
        )

        # ECS cluster

        cluster = ecs.Cluster(
            self, 'Cluster',
            vpc=vpc
        )

        consoleme_imported_alb = lb.ApplicationLoadBalancer.from_application_load_balancer_attributes(
            self,
            'ConsolemeImportedALB',
            load_balancer_arn=consoleme_alb.load_balancer_arn,
            vpc=vpc,
            security_group_id=consoleme_sg.security_group_id,
            load_balancer_dns_name=consoleme_alb.load_balancer_dns_name
        )

        consoleme_ecs_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            'Service',
            cluster=cluster,
            task_definition=consoleme_ecs_task_definition,
            load_balancer=consoleme_imported_alb,
            security_groups=[consoleme_sg],
            open_listener=False
        )

        consoleme_ecs_service.target_group.configure_health_check(
            path='/',
            enabled=True,
            healthy_http_codes='200-302'
        )

        consoleme_ecs_service_scaling_target = applicationautoscaling.ScalableTarget(
            self,
            'AutoScalingGroup',
            max_capacity=config_yaml['max_capacity'],
            min_capacity=config_yaml['min_capacity'],
            resource_id='service/' + cluster.cluster_name + '/' + consoleme_ecs_service.service.service_name,
            scalable_dimension='ecs:service:DesiredCount',
            service_namespace=applicationautoscaling.ServiceNamespace.ECS,
            role=iam.Role(
                self,
                'AutoScaleRole',
                assumed_by=iam.ServicePrincipal(service='ecs-tasks.amazonaws.com'),
                description='Role for ECS auto scaling group',
                managed_policies=[
                    iam.ManagedPolicy.from_managed_policy_arn(
                        self,
                        'AutoScalingManagedPolicy',
                        managed_policy_arn='arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceAutoscaleRole'
                    )
                ]
            )
        )

        applicationautoscaling.TargetTrackingScalingPolicy(
            self,
            'AutoScalingPolicy',
            scaling_target=consoleme_ecs_service_scaling_target,
            scale_in_cooldown=cdk.Duration.seconds(amount=10),
            scale_out_cooldown=cdk.Duration.seconds(amount=10),
            target_value=50,
            predefined_metric=applicationautoscaling.PredefinedMetric.ECS_SERVICE_AVERAGE_CPU_UTILIZATION
        )

        consoleme_imported_alb.add_listener(
            'ConsolemeALBListener',
            protocol=lb.ApplicationProtocol.HTTPS,
            port=443,
            certificates=[certificate],
            default_action=lb.ListenerAction.forward(
                target_groups=[consoleme_ecs_service.target_group])
        )
