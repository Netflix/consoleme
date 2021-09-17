# Central Account

The ConsoleMe service needs its own user or role. Note that ConsoleMe has a lot of permissions. You should ensure that its privileges cannot be used outside of ConsoleMe, except by authorized administrators \(Likely, you\).

You can call this new role "ConsoleMeInstanceProfile". It will also need to assume whichever roles you want to allow it to assume in your environment. Here is a full-fledged policy you can use when deploying to production. For now, scoping down assume role rights for testing should be sufficient. Create an inline policy for your role with the following permissions if you never want to have to think about it again:

Replace `arn:aws:iam::1243456789012:role/consolemeInstanceProfile` in the Assume Role Trust Policy with your ConsoleMe service role ARN.

```text
{
  "Statement": [
    {
      "Action": [
        "access-analyzer:*",
        "cloudtrail:*",
        "cloudwatch:*",
        "config:SelectResourceConfig",
        "config:SelectAggregateResourceConfig",
        "dynamodb:batchgetitem",
        "dynamodb:batchwriteitem",
        "dynamodb:deleteitem",
        "dynamodb:describe*",
        "dynamodb:getitem",
        "dynamodb:getrecords",
        "dynamodb:getsharditerator",
        "dynamodb:putitem",
        "dynamodb:query",
        "dynamodb:scan",
        "dynamodb:updateitem",
        "dynamodb:CreateTable",
        "dynamodb:UpdateTimeToLive",
        "sns:createplatformapplication",
        "sns:createplatformendpoint",
        "sns:deleteendpoint",
        "sns:deleteplatformapplication",
        "sns:getendpointattributes",
        "sns:getplatformapplicationattributes",
        "sns:listendpointsbyplatformapplication",
        "sns:publish",
        "sns:setendpointattributes",
        "sns:setplatformapplicationattributes",
        "sts:assumerole"
      ],
      "Effect": "Allow",
      "Resource": ["*"]
    },
    {
      "Action": ["ses:sendemail", "ses:sendrawemail"],
      "Condition": {
        "StringLike": {
          "ses:FromAddress": ["email_address_here@example.com"]
        }
      },
      "Effect": "Allow",
      "Resource": "arn:aws:ses:*:123456789:identity/your_identity.example.com"
    },
    {
      "Action": [
        "autoscaling:Describe*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "config:BatchGet*",
        "config:List*",
        "config:Select*",
        "ec2:DescribeSubnets",
        "ec2:describevpcendpoints",
        "ec2:DescribeVpcs",
        "iam:GetAccountAuthorizationDetails",
        "iam:ListAccountAliases",
        "iam:ListAttachedRolePolicies",
        "ec2:describeregions",
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
      "Resource": "*"
    }
  ],
  "Version": "2012-10-17"
}
```

You must also allow ConsoleMe to read/write to the bucket you've decided to use to cache data. Please replace `BUCKET_NAME` below with the name of the bucket you will cache data in. This bucket must be in the same account as this role, and it must also be defined in your ConsoleMe configuration under the `consoleme_s3_bucket` configuration key. You can add this as a new inline policy on your ConsoleMeInstanceProfile role, or append the statement to an existing inline policy.

```text
{
    "Statement": [
        {
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::BUCKET_NAME",
                "arn:aws:s3:::BUCKET_NAME/*"
            ]
        }
    ]
}
```

Configure the trust policy with the following settings \(Yes, you'll want to give ConsoleMeInstanceProfile the ability to assume itself\):

```text
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      }
    },
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::1243456789012:role/consolemeInstanceProfile"
      }
    }
  ],
  "Version": "2012-10-17"
}
```

