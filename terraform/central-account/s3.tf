resource "random_string" "omnipotence" {
  length  = 4
  special = false
  number  = false
  upper   = false
}

resource "aws_s3_bucket" "consoleme_files_bucket" {
  bucket = "${lower(var.bucket_name_prefix)}-${random_string.omnipotence.result}"
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  force_destroy = true
  tags          = merge(tomap({ "Name" = var.bucket_name_prefix }), var.default_tags)
}

resource "aws_s3_bucket_object" "consoleme_config" {
  bucket = aws_s3_bucket.consoleme_files_bucket.bucket
  key    = "config.yaml"

  content = templatefile("${path.module}/templates/config_terraform.yaml", tomap({
    demo_target_role_arn                               = aws_iam_role.consoleme_target.arn
    demo_app_role_arn_1                                = aws_iam_role.consoleme_example_app_role_1.arn
    demo_app_role_arn_2                                = aws_iam_role.consoleme_example_app_role_2.arn
    demo_user_role_arn_1                               = aws_iam_role.consoleme_example_user_role_1.arn
    demo_user_role_arn_2                               = aws_iam_role.consoleme_example_user_role_2.arn
    current_account_id                                 = data.aws_caller_identity.current.account_id
    sync_accounts_from_organizations                   = var.sync_accounts_from_organizations
    sync_accounts_from_organizations_master_account_id = var.sync_accounts_from_organizations_master_account_id != null ? var.sync_accounts_from_organizations_master_account_id : data.aws_caller_identity.current.account_id
    sync_accounts_from_organizations_role_to_assume    = var.sync_accounts_from_organizations_role_to_assume
    application_admin                                  = var.application_admin
    region                                             = data.aws_region.current.name
    jwt_email_key                                      = var.lb-authentication-jwt-email-key
    jwt_groups_key                                     = var.lb-authentication-jwt-groups-key
    user_facing_url                                    = var.user_facing_url == "" ? "https://${aws_lb.public-to-private-lb.dns_name}:${var.lb_port}" : var.user_facing_url
    logout_url                                         = var.logout_url
  }))
}
