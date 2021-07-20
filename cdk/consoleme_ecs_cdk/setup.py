"""
Setup tools for consoleme_ecs_service cdk library
"""

import setuptools

with open("../README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="consoleme_ecs_cdk",
    version="0.0.1",
    description="AWS CDK stack for ConsoleMe ECS service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Avishay Bar",
    package_dir={"": "service"},
    packages=setuptools.find_packages(where="service"),
    install_requires=[
        "aws-cdk.core>=1.107.0",
        "aws-cdk.aws_s3>=1.107.0",
        "aws-cdk.aws-s3-deployment>=1.107.0",
        "aws-cdk.aws-iam>=1.107.0",
        "aws-cdk.aws-cognito>=1.107.0",
        "aws-cdk.aws_ec2>=1.107.0",
        "aws-cdk.aws_ecs>=1.107.0",
        "aws-cdk.aws-ecs-patterns>=1.107.0",
        "aws-cdk.aws-ecr-assets>=1.107.0",
        "aws-cdk.aws_efs>=1.107.0",
        "aws_cdk.aws_certificatemanager>=1.107.0",
        "aws_cdk.aws_route53>=1.107.0",
        "aws_cdk.aws_route53_targets>=1.107.0",
        "aws_cdk.aws_elasticloadbalancingv2>=1.107.0",
        "aws_cdk.aws_logs>=1.107.0",
        "aws_cdk.aws_kms>=1.107.0",
        "aws_cdk.aws_elasticache>=1.107.0",
        "aws_cdk.aws_dynamodb>=1.107.0",
        "aws_cdk.custom_resources>=1.107.0",
        "aws_cdk.aws_lambda>=1.107.0",
        "aws_cdk.aws-applicationautoscaling>=1.107.0",
        "PyYAML>=5.3.1",
        "pipreqs>=0.4.10",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
