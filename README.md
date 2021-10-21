[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-386/)
[![Discord](https://img.shields.io/discord/730908778299523072?label=Discord&logo=discord&style=flat-square)](https://discord.gg/nQVpNGGkYu)

# ConsoleMe

Check out our [quick start guide](https://hawkins.gitbook.io/consoleme/quick-start)
, [documentation](https://hawkins.gitbook.io/consoleme/)
, [feature videos](https://hawkins.gitbook.io/consoleme/feature-videos)
, [ReInvent Talk](https://www.youtube.com/watch?v=fXNRYcNyw0c&t=5s),
and [Blog Post](https://netflixtechblog.com/consoleme-a-central-control-plane-for-aws-permissions-and-access-fd09afdd60a8)
.

## Overview

ConsoleMe is a web service that makes AWS IAM permissions and credential management easier for end-users and cloud
administrators.

ConsoleMe provides [**numerous
ways**](https://hawkins.gitbook.io/consoleme/feature-videos/credentials/aws-console-login) to log in to the AWS Console.

An [**IAM Self-Service
Wizard**](https://hawkins.gitbook.io/consoleme/feature-videos/policy-management/self-service-iam-wizard) lets users
request IAM permissions in plain English. Cross-account resource policies will be automatically generated, and can be
applied with a single click for certain resource types.

[Weep](https://github.com/Netflix/weep) (ConsoleMe’s CLI) supports [**5 different
ways**](https://hawkins.gitbook.io/consoleme/weep-cli/cli) of serving AWS credentials locally.

Cloud administrators can [**create/clone IAM
roles**](https://hawkins.gitbook.io/consoleme/feature-videos/policy-management/role-creation-and-cloning) and natively [**manage
IAM roles, users, inline/managed policies, S3 Buckets, SQS queues, and SNS
topics**](https://hawkins.gitbook.io/consoleme/feature-videos/policy-management/policy-editor-for-iam-sqs-sns-and-s3)
across hundreds of accounts in a single interface.

Users can access most of your cloud resources in the AWS Console with a [**single
click**](https://hawkins.gitbook.io/consoleme/feature-videos/policy-management/multi-account-policies-management). Cloud
administrators can configure ConsoleMe to authenticate users through [**ALB
Authentication**](https://hawkins.gitbook.io/consoleme/configuration/authentication-and-authorization/alb-auth),
[**OIDC/OAuth2**](https://hawkins.gitbook.io/consoleme/configuration/authentication-and-authorization/oidc-oauth2-okta),
or [**SAML**](https://hawkins.gitbook.io/consoleme/configuration/authentication-and-authorization/saml-auth0).

… And more. Check out our [docs](https://hawkins.gitbook.io/consoleme/) to get started.

## Project resources

- [Discord](https://discord.gg/nQVpNGGkYu)
- [Docs](https://hawkins.gitbook.io/consoleme/)
- [Weep (our CLI)](https://github.com/netflix/weep)
- [Source Code](https://github.com/netflix/consoleme)
- [Issue tracker](https://github.com/netflix/consoleme/issues)
- [Blog Post](https://netflixtechblog.com/consoleme-a-central-control-plane-for-aws-permissions-and-access-fd09afdd60a8)
- [ReInvent Talk](https://www.youtube.com/watch?v=fXNRYcNyw0c&t=5s)
- [Anonymous Feedback Form](https://forms.gle/JVgmHVua3Tr7JVsr9)

## Third Party Mentions

- [Achieving least-privilege at FollowAnalytics with Repokid, Aardvark and ConsoleMe](https://medium.com/followanalytics/granting-least-privileges-at-followanalytics-with-repokid-aardvark-and-consoleme-895d8daf604a)
- [Netflix’s ConsoleMe local installation on Linux machine](https://kerneltalks.com/tools/netflixs-consoleme-local-installation-on-linux-machine/)
- [Improving database security at FollowAnalytics with AWS IAM database authentication and ConsoleMe](https://medium.com/followanalytics/improving-database-security-at-followanalytics-with-aws-iam-database-authentication-and-consoleme-d00ea8a6edef)
- [Awesome IAM Policy Tools](https://github.com/kdeldycke/awesome-iam#aws-policy-tools)
- [Netflix on AWS Case Study](https://aws.amazon.com/solutions/case-studies/netflix/)
- [Netflix Open Sources ConsoleMe to Manage Permissions and Access on AWS](infoq.com/news/2021/04/netflix-consoleme-aws/)

## Companies that use ConsoleMe (alphabetically sorted)

- [AB180](https://en.ab180.co/)
- [Calm](https://www.calm.com/)
- [FollowAnalytics](https://followanalytics.com/)
- [myKaarma](https://mykaarma.com/)
- [National Center for Biotechnology Information](https://www.ncbi.nlm.nih.gov/)
- Feel free to submit a PR or let us know in an [Issue](https://github.com/Netflix/consoleme/issues) if you'd like to
  add your company to this list.
