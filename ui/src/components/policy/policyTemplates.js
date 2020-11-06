const templateOptions = [
  {
    key: "default",
    value: JSON.stringify({
      Statement: [
        {
          Action: [""],
          Effect: "Allow",
          Resource: [""],
        },
      ],
      Version: "2012-10-17",
    }),
    text: "Default Template",
  },
  {
    key: "s3read",
    value: JSON.stringify({
      Statement: [
        {
          Action: ["s3:ListBucket", "s3:GetObject"],
          Effect: "Allow",
          Resource: [
            "arn:aws:s3:::BUCKET_NAME",
            "arn:aws:s3:::BUCKET_NAME/OPTIONAL_PREFIX/*",
          ],
          Sid: "s3readonly",
        },
      ],
    }),
    text: "S3 Read Access",
  },
  {
    key: "s3_write_access",
    value: JSON.stringify({
      Statement: [
        {
          Action: [
            "s3:ListBucket",
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
          ],
          Effect: "Allow",
          Resource: [
            "arn:aws:s3:::BUCKET_NAME",
            "arn:aws:s3:::BUCKET_NAME/OPTIONAL_PREFIX/*",
          ],
          Sid: "s3readwrite",
        },
      ],
    }),
    text: "S3 Write Access",
  },
  {
    key: "sqs",
    value: JSON.stringify({
      Statement: [
        {
          Action: [
            "sqs:ReceiveMessage",
            "sqs:SendMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueUrl",
            "sqs:GetQueueAttributes",
          ],
          Effect: "Allow",
          Resource: "QUEUE_ARN",
        },
      ],
    }),
    text: "SQS",
  },
  {
    key: "sns",
    value: JSON.stringify({
      Statement: [
        {
          Action: ["sns:Publish", "sns:Subscribe", "sns:Unsubscribe"],
          Effect: "Allow",
          Resource: "TOPIC_ARN",
        },
      ],
    }),
    text: "SNS",
  },
  {
    key: "rdspassrole",
    value: JSON.stringify({
      Statement: [
        {
          Action: ["iam:PassRole"],
          Effect: "Allow",
          Resource: "arn:aws:iam::<ACCOUNTID>:role/rds-monitoring-role",
        },
      ],
    }),
    text: "RDS Monitoring PassRole",
  },
  {
    key: "sts",
    value: JSON.stringify({
      Statement: [
        {
          Action: ["sts:AssumeRole"],
          Effect: "Allow",
          Resource: "arn:aws:iam::ACCOUNT_NUMBER:role/ROLE",
        },
      ],
    }),
    text: "STS - Assume role",
  },
  {
    key: "route53",
    value: JSON.stringify({
      Statement: [
        {
          Action: [
            "route53:changeresourcerecordsets",
            "route53:listresourcerecordsets",
          ],
          Resource: ["*"],
          Effect: "Allow",
        },
      ],
    }),
    text: "Route53 List/Change Record Sets",
  },
  {
    key: "ec2_create_volume",
    value: JSON.stringify({
      Statement: [
        {
          Action: [
            "ec2:attachvolume",
            "ec2:createvolume",
            "ec2:describelicenses",
            "ec2:describevolumes",
            "ec2:detachvolume",
            "ec2:reportinstancestatus",
            "ec2:resetsnapshotattribute",
          ],
          Resource: ["*"],
          Effect: "Allow",
        },
      ],
    }),
    text: "EC2 Volmount",
  },
  {
    key: "eni_auto_attach",
    value: JSON.stringify({
      Statement: [
        {
          Action: [
            "ec2:AttachNetworkInterface",
            "ec2:Describe*",
            "ec2:DetachNetworkInterface",
          ],
          Effect: "Allow",
          Resource: ["*"],
          Sid: "eniauto",
        },
      ],
      Version: "2012-10-17",
    }),
    text: "ENI - Auto attach",
  },
  {
    key: "ec2_ipv6",
    value: JSON.stringify({
      Statement: [
        {
          Action: ["ec2:AssignIpv6Addresses"],
          Effect: "Allow",
          Resource: ["*"],
        },
      ],
    }),
    text: "EC2 - AssignIpv6Addresses",
  },
  {
    key: "volmount",
    value: JSON.stringify({
      Statement: [
        {
          Action: [
            "ec2:attachvolume",
            "ec2:createsnapshot",
            "ec2:createtags",
            "ec2:createvolume",
            "ec2:deletesnapshot",
            "ec2:describeinstances",
            "ec2:describetags",
            "ec2:describevolumes",
            "ec2:modifyinstanceattribute",
          ],
          Effect: "Allow",
          Resource: ["*"],
        },
      ],
    }),
    text: "EC2 - volmount",
  },
];

export default templateOptions;
