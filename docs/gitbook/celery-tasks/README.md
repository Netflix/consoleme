# Celery Tasks

ConsoleMe uses [**Celery**](https://docs.celeryproject.org/en/stable/getting-started/introduction.html) to run tasks on schedule or on demand. Celery consists of one scheduler, and number of workers.

[ConsoleMe's celery tasks](https://github.com/Netflix/consoleme/blob/master/consoleme/celery_tasks/celery_tasks.py) perform the following functions:

<table>
  <thead>
    <tr>
      <th style="text-align:left">Task Name</th>
      <th style="text-align:left">Description</th>
      <th style="text-align:left">Frequency</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align:left">cache_iam_resources_across_accounts</td>
      <td style="text-align:left">Retrieves a list of your AWS accounts. In your primary region, this task
        will invoke a celery task ( cache_iam_resources_for_account ) for each account.
        In other regions, ConsoleMe will attempt to retreive this information from
        your<code>consoleme_iamroles_global</code> global DynamoDB table to sync roles.</td>
      <td
      style="text-align:left">Every 45 minutes</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_iam_resources_for_account</td>
      <td style="text-align:left">Retrieves and caches a list of IAM principals and policies for the current account. Stores
        data in DynamoDB, Redis, and (optionally) S3.</td>
      <td style="text-align:left">On demand</td>
    </tr>
    <tr>
      <td style="text-align:left">clear_old_redis_iam_cache</td>
      <td style="text-align:left">Deletes IAM roles that haven&apos;t been updated in the last 6 hours.</td>
      <td
      style="text-align:left">Every 6 hours</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_policies_table_details</td>
      <td style="text-align:left">Generates and caches the data needed to render the <a href="../feature-videos/policy-management/multi-account-policies-management.md">Policies Table</a>.</td>
      <td
      style="text-align:left">Every 30 minutes</td>
    </tr>
    <tr>
      <td style="text-align:left">report_celery_last_success_metrics</td>
      <td style="text-align:left">Reports metrics on when a celery task was last successful. These metrics
        are useful for alerting, and verifying the health of your ConsoleMe deployment.</td>
      <td
      style="text-align:left">Every minute</td>
    </tr>
    <tr>
      <td style="text-align:left">
        <p>cache_managed_policies</p>
        <p>_across_accounts</p>
      </td>
      <td style="text-align:left">Retrieves a list of your AWS accounts and invokes a celery task ( cache_managed_policies_for_account
        ) for each account.</td>
      <td style="text-align:left">Every 45 minutes</td>
    </tr>
    <tr>
      <td style="text-align:left">
        <p>cache_managed_policies</p>
        <p>_for_account</p>
      </td>
      <td style="text-align:left">Caches a list of IAM managed policies for the requested account. Used
        for the managed policy typeahead in the IAM policy editor.</td>
      <td style="text-align:left">On demand</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_s3_buckets_across_accounts</td>
      <td style="text-align:left">Retrieves a list of your AWS accounts and invokes a celery task ( cache_s3_buckets_for_account
        ) for each account.</td>
      <td style="text-align:left">Every 45 minutes</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_s3_buckets_for_account</td>
      <td style="text-align:left">Caches a list of S3 buckets for the requested account.</td>
      <td style="text-align:left">On demand</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_sqs_queues_across_accounts</td>
      <td style="text-align:left">Retrieves a list of your AWS accounts and invokes a celery task ( cache_sqs_queues_for_account
        ) for each account.</td>
      <td style="text-align:left">Every 45 minutes</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_sqs_queues_for_accounts</td>
      <td style="text-align:left">Caches a list of SQS queues for the requested account.</td>
      <td style="text-align:left">On demand</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_sns_topics_across_accounts</td>
      <td style="text-align:left">Retrieves a list of your AWS accounts and invokes a celery task ( cache_sns_topics_for_account
        ) for each account.</td>
      <td style="text-align:left">Every 45 minutes</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_sns_topics_for_account</td>
      <td style="text-align:left">Caches a list of SNS topics for the requested account.</td>
      <td style="text-align:left">On demand</td>
    </tr>
    <tr>
      <td style="text-align:left">get_iam_role_limit</td>
      <td style="text-align:left">Generates a ratio of IAM roles to max IAM roles for each of our accounts,
        and emits this as a metric that you can alert on.</td>
      <td style="text-align:left">Every 24 hours</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_cloudtrail_errors_by_arn</td>
      <td style="text-align:left">Uses your internal logic to generate a mapping of recent cloudtrail errors
        by ARN. This is shown on the policy editor page to your end-users.</td>
      <td
      style="text-align:left">Every 1 hour</td>
    </tr>
    <tr>
      <td style="text-align:left">
        <p>cache_resources_from_</p>
        <p>aws_config_across_accounts</p>
      </td>
      <td style="text-align:left">Retrieves a list of your AWS accounts and invokes a celery task ( cache_resources_from_aws_config_for_account
        ) for each account.</td>
      <td style="text-align:left">Every 1 Hour</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_policy_requests</td>
      <td style="text-align:left">Caches all of your policy requests from DynamoDB to Redis. Used by the <code>/requests</code> endpoint.</td>
      <td
      style="text-align:left">Every 1 Hour</td>
    </tr>
    <tr>
      <td style="text-align:left">cache_cloud_account_mapping</td>
      <td style="text-align:left">Retrieves and caches details about your AWS accounts. Retrieval depends
        on <a href="../configuration/account-syncing.md">configuration</a>.</td>
      <td
      style="text-align:left">Every 1 Hour</td>
    </tr>
    <tr>
      <td style="text-align:left">
        <p>cache_credential_authorization</p>
        <p>_mapping</p>
      </td>
      <td style="text-align:left"><a href="../configuration/role-credential-authorization/">Generates and caches a mapping of groups/users to IAM roles</a>.
        This is used to determine authorization for role credentials.</td>
      <td style="text-align:left">Every 5 minutes</td>
    </tr>
  </tbody>
</table>

