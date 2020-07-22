data "aws_iam_policy_document" "consoleme_target" {
  statement {
    sid       = "ConsoleMeWillAccessThis"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "ec2:DescribeInstances",
      "s3:GetObject",
      "s3:ListAllMyBuckets"
    ]
  }
}

resource "aws_iam_policy" "consoleme_target" {
  name   = "ConsoleMeTargetPolicy"
  path   = "/"
  policy = data.aws_iam_policy_document.consoleme_target.json
}

data "aws_iam_policy_document" "consoleme_target_trust_policy" {
  statement {
    sid    = "AssumeRoleEC2"
    effect = "Allow"
    actions = [
      "sts:AssumeRole"
    ]
    principals {
      identifiers = [
        "ec2.amazonaws.com"
      ]
      type = "Service"
    }
  }

  statement {
    sid     = "ConsoleMeAssumesTarget"
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      identifiers = [aws_iam_role.ConsoleMeInstanceProfile.arn]
      type        = "AWS"
    }
  }
}

resource "aws_iam_role" "consoleme_target" {
  name               = "ConsoleMeTarget"
  assume_role_policy = data.aws_iam_policy_document.consoleme_target_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "consoleme_target" {
  role       = aws_iam_role.consoleme_target.name
  policy_arn = aws_iam_policy.consoleme_target.arn
}
