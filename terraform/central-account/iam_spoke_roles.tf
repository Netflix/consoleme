# This role should be distributed across all of your accounts

data "aws_iam_policy_document" "consoleme_target" {
  statement {
    sid       = "ConsoleMeWillAccessThis"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "autoscaling:Describe*",
      "cloudwatch:Get*",
      "cloudwatch:List*",
      "config:BatchGet*",
      "config:List*",
      "config:Select*",
      "ec2:DescribeInstances",
      "ec2:DescribeRegions",
      "ec2:DescribeSubnets",
      "ec2:DescribeVpcs",
      "ec2:describevpcendpoints",
      "iam:*",
      "s3:GetBucketPolicy",
      "s3:GetBucketTagging",
      "s3:GetObject",
      "s3:ListAllMyBuckets",
      "s3:ListAllMyBuckets",
      "s3:ListBucket",
      "s3:PutBucketPolicy",
      "s3:PutBucketTagging",
      "servicequotas:*",
      "sns:GetTopicAttributes",
      "sns:ListTagsForResource",
      "sns:ListTopics",
      "sns:SetTopicAttributes",
      "sns:TagResource",
      "sns:UnTagResource",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListQueueTags",
      "sqs:ListQueues",
      "sqs:SetQueueAttributes",
      "sqs:TagQueue",
      "sqs:UntagQueue"
    ]
  }
}

resource "aws_iam_role_policy" "consoleme_target_role_policy" {
  name   = "ConsoleMeTargetPolicy"
  role   = aws_iam_role.consoleme_target.id
  policy = data.aws_iam_policy_document.consoleme_target.json
}

data "aws_iam_policy_document" "consoleme_target_trust_policy" {
  statement {
    sid = "ConsoleMeAssumesTarget"
    actions = [
    "sts:AssumeRole"]
    effect = "Allow"
    principals {
      identifiers = [
      aws_iam_role.ConsoleMeInstanceProfile.arn]
      type = "AWS"
    }
  }
}

resource "aws_iam_role" "consoleme_target" {
  name               = "ConsoleMeTarget"
  assume_role_policy = data.aws_iam_policy_document.consoleme_target_trust_policy.json
}
