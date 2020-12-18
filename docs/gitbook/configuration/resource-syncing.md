# AWS Resource Syncing

ConsoleMe will be much more useful if it knows about your AWS resources.

ConsoleMe learns about the bulk of its resources from **AWS Config**, but will also attempt to sync IAM roles, SQS queues, SNS topics, and S3 buckets from their respective APIs.

ConsoleMe's [Celery Tasks](https://github.com/Netflix/consoleme/blob/master/consoleme/celery/celery_tasks.py) do the bulk of the syncing. The Docker-Compose flow defined in the [Quick Start](../quick-start/) guide starts a Celery container, with a worker and a scheduler that will attempt to cache your resources with your existing AWS credentials when ran.

Configure AWS Config to record all of the resource types that you care about \([Instructions](https://docs.aws.amazon.com/config/latest/developerguide/gs-console.html)\), and ensure that the role ConsoleMe assumes in each of your accounts has access to query AWS Config.

