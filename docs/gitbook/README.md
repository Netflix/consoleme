---
description: What is ConsoleMe?
---

# About

ConsoleMe is a multi-account AWS Swiss Army knife, making AWS usage easier for end-users and cloud administrators alike.

ConsoleMe achieves this through:

* consolidating the management of multiple accounts into a single web interface.
* allowing end-users and administrators to get credentials and console access to your onboarded accounts based on their authorization level.
* providing mechanisms for end-users and administrators to request and manage permissions for IAM roles, S3 buckets, SQS queues, SNS topics, and more.
* surfacing a powerful self-service wizard which empowers users to express their high-level intent and request the permissions right for them

## Extending ConsoleMe

ConsoleMe is extensible and pluggable. We offer a set of basic plugins for authenticating users, determining their groups and eligible roles, and more through the use of default plugins \([consoleme/default\_plugins](https://github.com/Netflix/consoleme/tree/master/consoleme/default_plugins%29%5C). If you need to customize ConsoleMe with internal business logic, we recommend creating a new private repository based on [consoleme/default\_plugins](https://github.com/Netflix/consoleme/tree/master/default_plugins) and modifying the code as appropriate to handle your use cases.

## Running Tasks with Celery

ConsoleMe uses [Celery](https://github.com/celery/celery/) to run various tasks on a schedule or on-demand. These tasks perform various quality of life operations such as data processing and caching but also allow for more advanced actions such as AWS Infrastructure updates and modifications. You can also add your custom celery tasks through the use of an internal plugin set. This means that you can implement internal-only Celery tasks with custom logic curated specifically to your needs. We provide an [example](https://github.com/Netflix/consoleme/blob/master/consoleme/default_plugins/plugins/celery_tasks/celery_tasks.py#L56) of this in our default\_plugins.

ConsoleMe's [open-source celery tasks](https://github.com/Netflix/consoleme/blob/master/consoleme/celery/celery_tasks.py#L1503) are generally used to cache resources across your AWS accounts \(such as IAM roles\) and report Celery metrics. We have tasks that perform the following:

* Cache IAM roles, SQS queues, SNS topics, and S3 buckets to Redis/DynamoDB
* Report Celery Last Success Metrics \(Used for alerting on failed tasks\)
* Cache Cloudtrail Errors by ARN

Netflix's internal celery tasks handle a variety of additional requirements that you may be interested in implementing yourself. These include:

* Caching S3/Cloudtrail errors from our Hive / ElasticSearch data sources. We expose these to end-users in our internal implementation of ConsoleMe.
* Generating tags for our resources, including the creator and owner of the resource and any applications associated with it.
* Generating and updating an IAM managed policy unique for each account which, when attached to a role, prevents the usage of the IAM role credentials from outside of that account. This is used as a safeguard against general credential theft and SSRF protection.
* Caching Google Groups, users, and account settings from internal services at Netflix.

## Contributing

Check out our [Contributing guide](contributing.md) to see how you can get involved with ConsoleMe and Weep.

