[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-386/)
[![Discord](https://img.shields.io/discord/730908778299523072?label=Discord&logo=discord&style=flat-square)](https://discord.gg/nQVpNGGkYu)

# ConsoleMe

Check out our [quick start guide](https://hawkins.gitbook.io/consoleme/quick-start), [documentation](https://hawkins.gitbook.io/consoleme/), [feature videos](https://hawkins.gitbook.io/consoleme/feature-videos), and [ReInvent Talk](https://virtual.awsevents.com/media/1_b8vc584c).

## Overview

Engineers that support a large AWS environment know how time consuming it is to manage IAM permissions for end-users. They realize how powerful it would be to let users request permissions in plain English, without having to understand complex permissions syntax, and without having to synchronously interact with cloud administrators.

They also realize that many solutions for managing AWS credentials are inflexible or insecure. It would be highly convenient if users relied on a single, centralized solution to get temporary, IP-restricted AWS credentials, and had a one-click way to access specific resources in the AWS console.

These are some of the things we were thinking about when we created ConsoleMe. We wanted a solution that would save time and steps for our users and admins, with the following attributes:

- Centralize non-machine access to AWS credentials
- Encourage least-privilege access and AWS permissions
- Provide a streamlined way to request AWS permissions
- Increase consistency in how permissions are granted
- Reduce operational burden and response time

ConsoleMe strives to be a multi-account AWS swiss-army knife, making AWS easier for your end-users and cloud administrators.
It is designed to consolidate the management of multiple accounts into a single web interface. It allows your end-users
and administrators to get credentials / console access to your different accounts, depending on their authorization
level. It provides mechanisms for end-users and administrators to both request and manage permissions for IAM roles,
S3 buckets, SQS queues, and SNS topics. A self-service wizard is also provided to guide users into requesting the
permissions they desire.

ConsoleMe is extensible and pluggable. We offer a set of basic plugins for authenticating users, determining their
groups and eligible roles, and more through the use of default plugins (consoleme/default_plugins).
If you need to link ConsoleMe with internal business logic, we recommend creating a new private repository
based on the default_plugins directory and modifying the code as appropriate to handle that custom internal logic.

ConsoleMe uses [Celery](https://github.com/celery/celery/) to run tasks on a schedule or on-demand. Our implementation
is also extensible through the usage of Python entry points. This means that you can also implement internal-only
Celery tasks to handle some of your custom business logic if needed.

The celery tasks in this repo are generally used to cache resources across your AWS accounts (such as IAM roles),
and report Celery metrics. We have tasks that perform the following:

- Cache IAM roles, SQS queues, SNS topics, and S3 buckets to Redis/DDB
- Report Celery Last Success Metrics (Used for alerting on failed tasks)
- Cache Cloudtrail Errors by ARN (This requires an internal celery task to aggregate Cloudtrail errors from your
  preferred source)

Netflix's internal celery tasks handle a variety of additional requirements that you may
be interested in implementing. These include:

- Caching S3/Cloudtrail errors from our Hive / ElasticSearch databases. We expose these to end-users in ConsoleMe
- Generating tags for our resources, which include the creator and owner of the resource, and any associated applications.
- Generating an IAM managed policy unique for each account which (when attached to a role) prevents the usage of an IAM
  role credential outside of the account. (This is used as a general credential theft and SSRF protection)
- Cache Google Groups, Users and Account Settings from internal services at Netflix

## Project resources

- [Discord](https://discord.gg/nQVpNGGkYu)
- [Docs](https://hawkins.gitbook.io/consoleme/)
- [Weep (our CLI)](https://github.com/netflix/weep)
- [Source Code](https://github.com/netflix/consoleme)
- [Issue tracker](https://github.com/netflix/consoleme/issues)
