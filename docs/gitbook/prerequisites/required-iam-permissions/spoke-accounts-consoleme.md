# Spoke Accounts

Each of your accounts needs a role that ConsoleMe can assume. It uses this role to cache information from the account. ConsoleMe will cache IAM roles, S3 buckets, SNS topics, and SQS queues by default. If you have it configured, it will also cache data from the AWS Config service for IAM policy/self-service typeahead and for the Policies table.

Note that these permissions are pretty hefty. Be sure to lock things down more here if appropriate for your environment, and again, ensure that this role is protected and can only be altered/use by administrative users.

Replace `arn:aws:iam::1243456789012:role/consolemeInstanceProfile` in the Assume Role Trust Policy with your ConsoleMe service role ARN.

```text
{
  "Statement": [
    {
      "Action": [
        "autoscaling:Describe*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "config:BatchGet*",
        "config:List*",
        "config:Select*",
        "ec2:describeregions",
        "ec2:DescribeSubnets",
        "ec2:describevpcendpoints",
        "ec2:DescribeVpcs",
        "iam:*",
        "s3:GetBucketPolicy",
        "s3:GetBucketTagging",
        "s3:ListAllMyBuckets",
        "s3:ListBucket",
        "s3:PutBucketPolicy",
        "s3:PutBucketTagging",
        "sns:GetTopicAttributes",
        "sns:ListTagsForResource",
        "sns:ListTopics",
        "sns:SetTopicAttributes",
        "sns:TagResource",
        "sns:UnTagResource",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ListQueues",
        "sqs:ListQueueTags",
        "sqs:SetQueueAttributes",
        "sqs:TagQueue",
        "sqs:UntagQueue"
      ],
      "Effect": "Allow",
      "Resource": ["*"],
      "Sid": "iam"
    }
  ],
  "Version": "2012-10-17"
}
```

Assume Role Policy Document:

```text
{
  "Statement": [
    {
      "Action": ["sts:AssumeRole", "sts:TagSession"],
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::1243456789012:role/consolemeInstanceProfile"
      }
    }
  ],
  "Version": "2012-10-17"
}
```

