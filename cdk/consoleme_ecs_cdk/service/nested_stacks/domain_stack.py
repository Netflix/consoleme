"""
Domain stack for running ConsoleMe on ECS
"""

from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_elasticloadbalancingv2 as lb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as route53_targets
from aws_cdk import core as cdk
from aws_cdk import custom_resources as cr

from consoleme_ecs_cdk.service.constants import (
    APPLICATION_PREFIX,
    HOSTED_ZONE_ID,
    HOSTED_ZONE_NAME,
)


class DomainStack(cdk.NestedStack):
    """
    Domain stack for running ConsoleMe on ECS
    """

    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        consoleme_alb: lb.ApplicationLoadBalancer,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        hosted_zone = route53.PublicHostedZone.from_hosted_zone_attributes(
            self,
            "HostedZone",
            hosted_zone_id=HOSTED_ZONE_ID,
            zone_name=HOSTED_ZONE_NAME,
        )

        route53_record = route53.ARecord(
            self,
            "LBRecord",
            zone=hosted_zone,
            record_name=APPLICATION_PREFIX,
            target=route53.RecordTarget(
                alias_target=(route53_targets.LoadBalancerTarget(consoleme_alb))
            ),
        )

        verify_ses_identity = cr.AwsCustomResource(
            self,
            "VerifySESIdentityResource",
            policy=cr.AwsCustomResourcePolicy.from_statements(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["ses:VerifyDomainIdentity", "ses:DeleteIdentity"],
                        resources=["*"],
                    )
                ]
            ),
            on_create=cr.AwsSdkCall(
                service="SES",
                action="verifyDomainIdentity",
                parameters={"Domain": route53_record.domain_name},
                physical_resource_id=cr.PhysicalResourceId.from_response(
                    "VerificationToken"
                ),
            ),
            on_delete=cr.AwsSdkCall(
                service="SES",
                action="deleteIdentity",
                parameters={"Identity": route53_record.domain_name},
            ),
            install_latest_aws_sdk=True,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        add_ses_dkim = cr.AwsCustomResource(
            self,
            "VerifySESDKIMResource",
            policy=cr.AwsCustomResourcePolicy.from_statements(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["ses:VerifyDomainDkim"],
                        resources=["*"],
                    )
                ]
            ),
            on_create=cr.AwsSdkCall(
                service="SES",
                action="verifyDomainDkim",
                parameters={"Domain": route53_record.domain_name},
                physical_resource_id=cr.PhysicalResourceId.of(
                    HOSTED_ZONE_ID + "VerifyDomainDKIM"
                ),
            ),
            install_latest_aws_sdk=True,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        add_ses_dkim.node.add_dependency(verify_ses_identity)

        certificate = acm.Certificate(
            self,
            "Certificate",
            domain_name="*." + hosted_zone.zone_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone=hosted_zone),
        )

        self.hosted_zone = hosted_zone
        self.certificate = certificate
        self.route53_record = route53_record
