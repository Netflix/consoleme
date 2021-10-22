# CloudTrail Integration via AWS Event Bridge

ConsoleMe can integrate with AWS CloudTrail via [Event Bridge](https://docs.amazonaws.cn/en_us/eventbridge/latest/userguide/eb-service-event.html). It can generate naive policies from CloudTrail Access Deny errors, and update IAM role cache based IAM create / update events.

If you're running ConsoleMe in a multi-account environment in a single AWS Organization, we recommend that you create an Event Bridge rule in **each region** of **each of your accounts** that will forward your CloudTrail data to a **single region in a single** **account** . The account that you choose to send this data to should be locked down, and only accessible by your cloud administrators.

The Event Bus on your central account \(The one where all of these logs will go to\) should have a resource-based policy allowing **all accounts within your organization** to send events to it. Here's what that might look like:

![](../.gitbook/assets/image%20%2817%29.png)

The rule on each region of each of your accounts should look similar to the below:

![](../.gitbook/assets/image%20%2813%29.png)

As previously mentioned, ConsoleMe only processes Access Deny and Role Update log messages. On your **central account**, we need two different rules. One for each scenario.

This first Event Bridge rule will help ConsoleMe to process AccessDenied  / UnauthorizedOperation errors from CloudTrail by sending them to an SNS topic. An SQS queue is subscribed to this topic, and ConsoleMe has the ability to read this SQS queue. Alternatively, the target for the event bridge rule could just be an SQS queue that ConsoleMe has access to. Setting this up is an exercise for the reader.

![](../.gitbook/assets/image%20%2826%29.png)

The second Event Bridge rule is needed for ConsoleMe to cache new or updated roles, as well as role authorization changes through tag updates, much quicker. The target can be an SNS topic, or an SQS queue.

![](../.gitbook/assets/image%20%2829%29.png)

After the rules are configured and you are seeing messages in your SQS queues, we need to modify ConsoleMe's configuration and restart ConsoleMe's celery scheduler / worker. Add the following configuration, replacing the queue ARNs as appropriate.

```text
celery:
  cache_cloudtrail_denies:
    enabled: true
  trigger_credential_mapping_refresh_from_role_changes:
    enabled: true
event_bridge:
  detect_role_changes_and_update_cache:
    queue_arn: arn:aws:sqs:{region}:{account_id}:consoleme-cloudtrail-role-events
    # assume_role: null <--- Optional role to assume to access the queue
  detect_cloudtrail_denies_and_update_cache:
    queue_arn: arn:aws:sqs:{region}:{account_id}:consoleme-cloudtrail-access-deny-events
    # assume_role: null <--- Optional role to assume to access the queue

```

You should begin to see role updates much quicker, and will also see access denied messaging for your IAM principals

![](../.gitbook/assets/image%20%2825%29.png)

