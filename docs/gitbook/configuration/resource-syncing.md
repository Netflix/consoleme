# AWS Resource Syncing

ConsoleMe learns about the bulk of your AWS resources from **AWS Config**, but will also attempt to sync IAM roles, SQS queues, SNS topics, and S3 buckets from their respective APIs. If you haven't enabled AWS Config yet, learn how to set it up [here](https://docs.aws.amazon.com/config/latest/developerguide/gs-console.html). Also, keep in mind that AWS Config is not free. Carefully decide which resource types to record.

{% hint style="info" %}
**Prerequisite**

Ensure that you've created identically named roles on each of your accounts \([Spoke Roles](../prerequisites/required-iam-permissions/spoke-accounts-consoleme.md)\) for ConsoleMe to assume, and that you've allowed the role ConsoleMe is using \([Central Account role](../prerequisites/required-iam-permissions/central-account-consolemeinstanceprofile.md)\) to assume those roles. This spoke role should also exist on the account ConsoleMe is on.
{% endhint %}

The example configuration below is a powerful one. It tells ConsoleMe which role it should assume on each of your spoke accounts before performing certain actions, such as querying AWS Config or updating policies for resources on the spoke account:

```text
policies:
  role_name: ConsoleMe
```

ConsoleMe's [Celery Tasks](https://github.com/Netflix/consoleme/blob/master/consoleme/celery/celery_tasks.py) do the bulk of the resource syncing. The Docker-Compose flow defined in the [Quick Start](../quick-start/) guide starts a Celery container, with a worker and a scheduler that will attempt to cache your resources with your existing AWS credentials when ran.

