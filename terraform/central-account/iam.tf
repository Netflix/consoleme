# ---------------------------------------------------------------------------------------------------------------------
# ConsoleMe Instance Profile permissions
# 1. Policy Document for ConsoleMe
# 2. IAM Policy resource for ConsoleMe in the ConsoleMe central account
# 3. Policy Document for the ConsoleMe
# ---------------------------------------------------------------------------------------------------------------------

data "aws_iam_policy_document" "ConsoleMeInstanceProfile" {
  statement {
    sid       = "CentralAccountPermissions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "cloudtrail:*",
      "cloudwatch:*",
      "config:*",
      "dynamodb:*",
      "iam:list*",
      "sns:*",
      "sqs:*",
      "sts:assumerole",
      "s3:GetObject"
    ]
  }
  statement {
    sid    = "SendEmail"
    effect = "Allow"
    actions = [
      "ses:sendemail",
      "ses:sendrawemail"
    ]
    resources = [
      "arn:aws:ses:*:${data.aws_caller_identity.current.account_id}:identity/${var.your_ses_identity}"
    ]
    condition {
      test     = "StringLike"
      variable = "ses:FromAddress"
      values   = var.email_addresses
    }
  }
}

resource "aws_iam_role_policy" "consoleme_target" {
  name   = "ConsoleMeInstanceProfilePolicy"
  role   = aws_iam_role.ConsoleMeInstanceProfile.id
  policy = data.aws_iam_policy_document.ConsoleMeInstanceProfile.json
}

# Allow SSM
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ConsoleMeInstanceProfile.id
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}


# ---------------------------------------------------------------------------------------------------------------------
# Trust Policy
# ---------------------------------------------------------------------------------------------------------------------

data "aws_iam_policy_document" "ConsoleMe_trust_policy" {
  statement {
    sid     = "AssumeRoleEC2"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      identifiers = ["ec2.amazonaws.com"]
      type        = "Service"
    }
  }

  //  statement {
  //    sid     = "AssumeRoleSelf"
  //    actions = ["sts:AssumeRole"]
  //    effect  = "Allow"
  //    principals {
  //      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.ConsoleMe_instance_profile_name}"]
  //      type        = "AWS"
  //    }
  //  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Instance Profile
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_iam_role" "ConsoleMeInstanceProfile" {
  name               = var.consoleme_instance_profile_name
  assume_role_policy = data.aws_iam_policy_document.ConsoleMe_trust_policy.json
}

resource "aws_iam_instance_profile" "ConsoleMeInstanceProfile" {
  name = var.consoleme_instance_profile_name
  role = aws_iam_role.ConsoleMeInstanceProfile.name
}

