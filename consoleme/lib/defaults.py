"""
Large default configuration values are stored here
"""
import yaml

SELF_SERVICE_IAM_DEFAULTS = yaml.safe_load(
    """
permissions_map:
  s3:
    text: S3 Bucket
    description: S3 Permissions
    inputs:
      - name: resource_arn
        type: typeahead_input
        text: Bucket Name
        required: true
        typeahead_endpoint: /policies/typeahead?resource=s3&show_full_arn_for_s3_buckets=true&search={query}
      - name: bucket_prefix
        type: text_input
        text: Prefix (Folder under S3 that you need access to).
        required: true
        default: /*
    action_map:
      - name: list
        text: List
        permissions:
          - s3:ListBucket
          - s3:ListBucketVersions
      - name: get
        text: Get
        permissions:
          - s3:GetObject
          - s3:GetObjectTagging
          - s3:GetObjectVersion
          - s3:GetObjectVersionTagging
          - s3:GetObjectAcl
          - s3:GetObjectVersionAcl
      - name: put
        text: Put
        permissions:
          - s3:PutObject
          - s3:PutObjectTagging
          - s3:PutObjectVersionTagging
          - s3:ListMultipartUploadParts*
          - s3:AbortMultipartUpload
      - name: delete
        text: Delete
        permissions:
          - s3:DeleteObject
          - s3:DeleteObjectTagging
          - s3:DeleteObjectVersion
          - s3:DeleteObjectVersionTagging
  sqs:
    text: SQS Queue
    description: ""
    inputs:
      - name: resource_arn
        type: typeahead_input
        text: Queue ARN
        required: true
        typeahead_endpoint: /policies/typeahead?resource=sqs&search={query}
    action_map:
      - name: send_messages
        text: Send Message (Queue Producer)
        permissions:
          - sqs:GetQueueAttributes
          - sqs:GetQueueUrl
          - sqs:SendMessage
      - name: receive_messages
        text: Receive/Delete Messages (Queue Consumer)
        permissions:
          - sqs:GetQueueAttributes
          - sqs:GetQueueUrl
          - sqs:ReceiveMessage
          - sqs:DeleteMessage
      - name: set_queue_attributes
        text: Set Queue Attributes
        permissions:
          - sqs:SetQueueAttributes
      - name: purge_messages
        text: Purge Queue (You monster!)
        permissions:
          - sqs:PurgeQueue
  sns:
    text: SNS Topic
    description: ""
    inputs:
      - name: resource_arn
        type: typeahead_input
        text: Topic ARN
        required: true
        typeahead_endpoint: /policies/typeahead?resource=sns&search={query}
    action_map:
      - name: get_topic_attributes
        text: Get Topic Attributes
        permissions:
          - sns:GetEndpointAttributes
          - sns:GetTopicAttributes
      - name: publish
        text: Publish
        permissions:
          - sns:Publish
      - name: subscribe
        text: Subscribe
        permissions:
          - sns:Subscribe
          - sns:ConfirmSubscription
      - name: unsubscribe
        text: Unsubscribe
        permissions:
          - sns:Unsubscribe
  rds:
    text: RDS
    description: ""
    inputs:
      - name: resource_arn
        type: text_input
        text: EC2 resource you need access to
        required: true
        default: "arn:aws:iam::{account_id}:role/rds-monitoring-role"
    action_map:
      - name: passrole
        text: PassRole
        permissions:
          - iam:PassRole
  ec2:
    text: EC2
    description: ""
    inputs:
      - name: resource_arn
        type: text_input
        text: EC2 resource you need access to
        required: true
        default: "*"
    action_map:
      - name: volmount
        text: VolMount
        permissions:
          - ec2:attachvolume
          - ec2:createvolume
          - ec2:describelicenses
          - ec2:describevolumes
          - ec2:detachvolume
          - ec2:reportinstancestatus
          - ec2:resetsnapshotattribute
      - name: ipv6
        text: Enable IPv6
        permissions:
          - ec2:AssignIpv6Addresses
  route53:
    text: Route53
    description: ""
    inputs:
      - name: resource_arn
        type: text_input
        text: Route53 Domain you need access to
        required: true
        default: "*"
    action_map:
      - name: list_records
        text: List Records
        permissions:
          - route53:listresourcerecordsets
      - name: change_records
        text: Change Records
        permissions:
          - route53:changeresourcerecordsets
  sts:
    text: STS AssumeRole
    description: ""
    inputs:
      - name: resource_arn
        type: typeahead_input
        text: Role ARN that you wish to assume
        required: true
        typeahead_endpoint: /policies/typeahead?resource=iam_arn&search={query}
    action_map:
      - name: assume_role
        text: Assume Role
        permissions:
          - sts:AssumeRole
  ses:
    text: SES - Send Email
    inputs:
      - name: from_address
        type: text_input
        text: Email Address to send from
        required: true
        default: "emailaddress@example.com"
      - name: resource_arn
        type: text_input
        text: ARN of the resource to send from
        required: true
    condition:
      StringLike:
        ses:FromAddress: "{from_address}"
    action_map:
      - name: send_email
        text: Send Email
        permissions:
          - ses:SendEmail
          - ses:SendRawEmail
  crud_lookup:
    text: Other
    description: |-
      Define the service (rds, route53, rekognition, etc), the resource (An ARN or a wildcard), and the list of actions
      (List, Read, Write, Permissions Management, Tagging) that you need access to. If you know the specific IAM
      permissions you need, use "Advanced Mode" from the dropdown instead.
    inputs:
      - name: service_name
        type: single_typeahead_input
        text: Service (s3, sqs, sns, rekognition, etc)
        required: true
        typeahead_endpoint: /api/v1/policyuniverse/autocomplete/?only_filter_services=true&prefix={query}
      - name: resource_arn
        type: typeahead_input
        text: Resource ARN or Wildcard (*)
        required: true
        typeahead_endpoint: /api/v2/typeahead/resources?typeahead={query}&ui_formatted=true
    action_map:
      - name: list
        text: List
        permissions:
          - List
      - name: read
        text: Read
        permissions:
          - Read
      - name: write
        text: Write
        permissions:
          - Write
      - name: permissions-management
        text: Permissions Management
        permissions:
          - Permissions management
      - name: tagging
        text: Tagging
        permissions:
          - Tagging"""
)

PERMISSION_TEMPLATE_DEFAULTS = yaml.safe_load(
    """
- key: default
  text: Default Template
  value: |-
    {
         "Statement":[
             {
                 "Action":[
                     ""
                 ],
                 "Effect":"Allow",
                 "Resource": [
                     ""
                 ]
             }
         ],
         "Version":"2012-10-17"
     }
- key: s3write
  text: S3 Write Access
  value: |-
    {
        "Statement":[
            {
                "Action":[
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                "Effect":"Allow",
                "Resource":[
                    "arn:aws:s3:::BUCKET_NAME",
                    "arn:aws:s3:::BUCKET_NAME/OPTIONAL_PREFIX/*"
                ],
                "Sid":"s3readwrite"
            }
        ]
    }
- key: s3read
  text: S3 Read Access
  value: |-
    {
        "Statement":[
            {
                "Action":[
                    "s3:ListBucket",
                    "s3:GetObject"
                ],
                "Effect":"Allow",
                "Resource":[
                    "arn:aws:s3:::BUCKET_NAME",
                    "arn:aws:s3:::BUCKET_NAME/OPTIONAL_PREFIX/*"
                ],
                "Sid":"s3readonly"
            }
        ]
    }
- key: sqs
  text: SQS
  value: |-
    {
      "Statement": [
        {
          "Action": [
            "sqs:ReceiveMessage",
            "sqs:SendMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueUrl",
            "sqs:GetQueueAttributes"
          ],
          "Effect": "Allow",
          "Resource": "QUEUE_ARN"
        }
      ]
    }
- key: sns
  text: SNS
  value: |-
    {
      "Statement": [
        {
          "Action": [
            "sns:Publish",
            "sns:Subscribe",
            "sns:Unsubscribe"
          ],
          "Effect": "Allow",
          "Resource": "TOPIC_ARN"
        }
      ]
    }
- key: rdspassrole
  text: RDS Monitoring PassRole
  value: |-
    {
      "Statement": [
        {
          "Action": [
            "iam:PassRole"
          ],
          "Effect": "Allow",
          "Resource": "arn:aws:iam::<ACCOUNTID>:role/rds-monitoring-role"
        }
      ]
    }
- key: ses
  text: SES
  value: |-
    {
        "Statement": [
            {
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Effect": "Allow",
                "Resource": "arn:aws:ses:*:123456789012:identity/example.com",
                "Condition": {
                    "StringLike": {
                        "ses:FromAddress": "SENDER@example.com"
                    }
                }
            }
        ]
    }
- key: sts
  text: STS - Assume role
  value: |-
    {
        "Statement": [
            {
                "Action": [
                    "sts:AssumeRole"
                ],
                "Effect": "Allow",
                "Resource": "arn:aws:iam::ACCOUNT_NUMBER:role/ROLE"
            }
        ]
    }
- key: route53
  text: Route53 List/Change Record Sets
  value: |-
    {
        "Statement": [
            {
                "Action": [
                    "route53:changeresourcerecordsets",
                    "route53:listresourcerecordsets"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            }
        ]
    }
- key: ec2_create_volume
  text: EC2 Volmount
  value: |-
    {
        "Statement": [
            {
                "Action": [
                    "ec2:attachvolume",
                    "ec2:createvolume",
                    "ec2:describelicenses",
                    "ec2:describevolumes",
                    "ec2:detachvolume",
                    "ec2:reportinstancestatus",
                    "ec2:resetsnapshotattribute"
                ],
                "Resource": [
                    "*"
                ],
                "Effect": "Allow"
            }
        ]
    }
- key: put_cloudwatch_data
  text: Cloudwatch - putmetricdata
  value: |-
    {
        "Statement":[
            {
                "Action":[
                    "cloudwatch:putmetricdata"
                ],
                "Effect":"Allow",
                "Resource":[
                    "*"
                ]
            }
        ],
        "Version":"2012-10-17"
    }
- key: eni_auto_attach
  text: ENI - Auto attach
  value: |-
    {
        "Statement":[
            {
                "Action":[
                    "ec2:AttachNetworkInterface",
                    "ec2:Describe*",
                    "ec2:DetachNetworkInterface"
                ],
                "Effect":"Allow",
                "Resource":[
                    "*"
                ],
                "Sid":"eniauto"
            }
        ],
        "Version":"2012-10-17"
    }
- key: ec2_ipv6
  text: EC2 - AssignIpv6Addresses
  value: |-
    {
        "Statement":[
            {
                "Action":[
                    "ec2:AssignIpv6Addresses"
                ],
                "Effect":"Allow",
                "Resource":[
                    "*"
                ]
            }
        ]
    }
- key: volmount
  text: EC2 - volmount
  value: |-
    {
        "Statement":[
            {
                "Action":[
                      "ec2:attachvolume",
                      "ec2:createsnapshot",
                      "ec2:createtags",
                      "ec2:createvolume",
                      "ec2:deletesnapshot",
                      "ec2:describeinstances",
                      "ec2:describetags",
                      "ec2:describevolumes",
                      "ec2:modifyinstanceattribute"
                ],
                "Effect":"Allow",
                "Resource":[
                    "*"
                ]
            }
        ]
    }
-   key: securitygroupmutate
    text: EC2 - Security Group Read/Write
    value: |-
      {
        "Statement": [
            {
                "Action": [
                    "ec2:authorizesecuritygroupingress",
                    "ec2:revokesecuritygroupingress"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:ec2:REGION:ACCOUNT_NUMBER:security-group/SECURITY_GROUP_ID"
                ],
                "Sid": "sgmutate"
            },
            {
                "Action": [
                    "ec2:describesecuritygroup*"
                ],
                "Effect": "Allow",
                "Resource": [
                    "*"
                ],
                "Sid": "sgdescribe"
            }
        ]
      }
"""
)
