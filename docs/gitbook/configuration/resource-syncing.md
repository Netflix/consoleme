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

If you need to only manage a subset of roles, you can limit the roles that will be displayed in the `/policies` page. You can limit the roles by referencing the tags on the roles and adding them to this configuration in Consoleme:

```text
roles:
  allowed_tags:
    tag1: value1
    tag2: value2
```
Note that all tag keys and values must match for a role to be allowed.

You can also allow roles based on a list of tag keys. The role will be allowed if any of the tag keys exist against it.

```text
roles:
  allowed_tag_keys:
    - consoleme-authorized
    - consoleme-authorized-cli-only
```

Alternatively, you can provide an explicit list of roles you want managed by Consoleme by adding this configuration:

```text
roles:
  allowed_arns:
    - arn:aws:iam::111111111111:role/role-name-here-1
    - arn:aws:iam::111111111111:role/role-name-here-2
    - arn:aws:iam::111111111111:role/role-name-here-3
    - arn:aws:iam::222222222222:role/role-name-here-1
    - arn:aws:iam::333333333333:role/role-name-here-1
```

By default, all policy types are presented on the `/policies` page. However, you can opt-out of caching and presenting policy types using this configuration:

```text
cache_policies_table_details:
  skip_iam_roles: true
  skip_iam_users: true
  skip_s3_buckets: true
  skip_sns_topics: true
  skip_sqs_queues: true
  skip_managed_policies: true
  skip_aws_config_resources: true
```

