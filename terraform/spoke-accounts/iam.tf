
data "aws_iam_policy_document" "consoleme" {
    statement {
        sid = "ConsoleMeTypeahead"
        effect = "Allow"
        resources = ["*"]
        actions = [
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
            "sqs:UntagQueue",
        ]
    }

}