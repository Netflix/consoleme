# ---------------------------------------------------------------------------------------------------------------------
# Consoleme Instance Profile permissions
# 1. Policy Document for Consoleme
# 2. IAM Policy resource for Consoleme in the Consoleme central account
# 3. Policy Document for the Consoleme
# ---------------------------------------------------------------------------------------------------------------------

data "aws_iam_policy_document" "consoleme" {
  statement {
    sid       = "1"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "cloudtrail:*",
      "cloudwatch:*",
      "config:*",
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
      "dynamodb:listtables",
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

resource "aws_iam_policy" "consoleme" {
  name   = "ConsoleMePolicy"
  path   = "/"
  policy = data.aws_iam_policy_document.consoleme.json
}

# ---------------------------------------------------------------------------------------------------------------------
# Trust Policy
# ---------------------------------------------------------------------------------------------------------------------

data "aws_iam_policy_document" "consoleme_trust_policy" {
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
  //      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.consoleme_instance_profile_name}"]
  //      type        = "AWS"
  //    }
  //  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Instance Profile
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_iam_role" "consoleme" {
  name               = var.consoleme_instance_profile_name
  assume_role_policy = data.aws_iam_policy_document.consoleme_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "consoleme" {
  role       = var.consoleme_instance_profile_name
  policy_arn = aws_iam_policy.consoleme.arn
}

resource "aws_iam_instance_profile" "consoleme" {
  name = var.consoleme_instance_profile_name
  role = aws_iam_role.consoleme.name
}