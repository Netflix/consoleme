---
description: What is ConsoleMe?
---

# About

ConsoleMe strives to be a multi-account AWS swiss-army knife, making AWS easier for your end-users and cloud administrators. It is designed to consolidate the management of multiple accounts into a single web interface. It allows your end-users and administrators to get credentials / console access to your different accounts, depending on their authorization level. It provides mechanisms for end-users and administrators to both request and manage permissions for IAM roles, S3 buckets, SQS queues, and SNS topics. A powerful self-service wizard makes it easy for users to express their intent and request the permissions they need.

ConsoleMe is extensible and pluggable. We offer a set of basic plugins for authenticating users, determining their groups and eligible roles, and more through the use of default plugins \([consoleme/default\_plugins](https://github.com/Netflix/consoleme/tree/master/default_plugins)\). If you need to customize ConsoleMe with internal business logic, we recommend creating a new private repository based on the default\_plugins directory and modifying the code as appropriate to handle all of your use cases.

ConsoleMe uses [Celery](https://github.com/celery/celery/) to run tasks on a schedule or on-demand. You can add custom, internal celery tasks through the use of an internal plugin set.  This means that you can also implement internal-only Celery tasks. We provide an [example](https://github.com/Netflix/consoleme/blob/master/default_plugins/consoleme_default_plugins/plugins/celery_tasks/celery_tasks.py#L56) in our default\_plugins.

ConsoleMe's [open-source celery tasks](https://github.com/Netflix/consoleme/blob/master/consoleme/celery/celery_tasks.py#L1503) are generally used to cache resources across your AWS accounts \(such as IAM roles\), and report Celery metrics. We have tasks that perform the following:

- Cache IAM roles, SQS queues, SNS topics, and S3 buckets to Redis/DynamoDB

- Report Celery Last Success Metrics \(Used for alerting on failed tasks\)

- Cache Cloudtrail Errors by ARN 

Netflix's internal celery tasks handle a variety of additional requirements that you may be interested in implementing yourself. These include:

- Caching S3/Cloudtrail errors from our Hive / ElasticSearch data sources. We expose these to end-users in our internal implementation of ConsoleMe

- Generating tags for our resources, which include the creator and owner of the resource, and any  applications associated with it.

- Generating and updating an IAM managed policy unique for each account which \(when attached to a role\) prevents the usage of the IAM role credentials from outside of that account. \(This is used as a general credential theft and SSRF protection\)

- Cache Google Groups, Users and Account Settings from internal services at Netflix

