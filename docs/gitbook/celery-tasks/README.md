# Celery Tasks

ConsoleMe uses [**Celery**](https://docs.celeryproject.org/en/stable/getting-started/introduction.html) ****to run tasks on schedule or on demand. Celery consists of one scheduler, and number of workers. 

[ConsoleMe's celery tasks](https://github.com/Netflix/consoleme/blob/master/consoleme/celery/celery_tasks.py#L1338) perform the following functions:

| Task Name | Description | Frequency |
| :--- | :--- | :--- |
| cache\_roles\_across\_accounts | Retrieves a list of your AWS accounts. In your primary region, this task will invoke a celery task \( cache\_roles\_for\_account \) for each account. In other regions, ConsoleMe will attempt to retreive this information from your`consoleme_iamroles_global` global DynamoDB table to sync. | Every 45 minutes |
| cache\_roles\_for\_account | Retrieves and caches a list of IAM roles for the current account. Stores data in DynamoDB, Redis, and \(optionally\) S3. | On demand |
| clear\_old\_redis\_iam\_cache | Deletes IAM roles that haven't been updated in the last 6 hours. | Every 6 hours |
| cache\_policies\_table\_details | Generates and caches the data needed to render the [Policies Table](../feature-videos/policy-management/multi-account-policies-management.md).  | Every 30 minutes |
| report\_celery\_last\_success\_metrics | Reports metrics on when a celery task was last successful. These metrics are useful for alerting, and verifying the health of your ConsoleMe deployment. | Every minute |
| cache\_managed\_policies\_across\_accounts | Retrieves a list of your AWS accounts  and invokes a celery task \( cache\_managed\_policies\_for\_account \) for each account. | Every 45 minutes |
| cache\_managed\_policies\_for\_account | Caches a list of IAM managed policies for the requested account. Used for the managed policy typeahead in the IAM policy editor. | On demand |
| cache\_s3\_buckets\_across\_accounts | Retrieves a list of your AWS accounts  and invokes a celery task \( cache\_s3\_buckets\_for\_account \) for each account. | Every 45 minutes |
| cache\_s3\_buckets\_for\_account | Caches a list of S3 buckets for the requested account. | On demand |
| cache\_sqs\_queues\_across\_accounts | Retrieves a list of your AWS accounts  and invokes a celery task \( cache\_sqs\_queues\_for\_account \) for each account. | Every 45 minutes |
| cache\_sqs\_queues\_for\_accounts | Caches a list of SQS queues for the requested account.  | On demand |
| cache\_sns\_topics\_across\_accounts | Retrieves a list of your AWS accounts  and invokes a celery task \( cache\_sns\_topics\_for\_account \) for each account. | Every 45 minutes |
| cache\_sns\_topics\_for\_account | Caches a list of SNS topics for the requested account.  | On demand |
| get\_iam\_role\_limit | Generates a ratio of IAM roles to max IAM roles for each of our accounts, and emits this as a metric that you can alert on. | Every 24 hours |
| cache\_cloudtrail\_errors\_by\_arn | Uses your internal logic to generate a mapping of recent cloudtrail errors by ARN. This is shown on the policy editor page to your end-users. | Every 1 hour |
| cache\_resources\_from\_aws\_config\_across\_accounts | Retrieves a list of your AWS accounts  and invokes a celery task \( cache\_resources\_from\_aws\_config\_for\_account \) for each account. | Every 1 Hour |
| cache\_policy\_requests | Caches all of your policy requests from DynamoDB to Redis. Used by the `/requests` endpoint. | Every 1 Hour |
| cache\_cloud\_account\_mapping | Retrieves and caches details about your AWS accounts. Retrieval depends on [configuration](../configuration/account-syncing.md). | Every 1 Hour |
| cache\_credential\_authorization\_mapping | [Generates and caches a mapping of groups/users to IAM roles](../configuration/role-credential-authorization/). This is used to determine authorization for role credentials.  | Every 5 minutes |





