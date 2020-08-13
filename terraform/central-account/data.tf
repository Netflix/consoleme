data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name = "name"
    values = [
    var.ec2_ami_name_filter]
  }

  owners = [
  var.ec2_ami_owner_filter]
}

data "template_file" "consoleme_config" {
  template = file("${path.module}/templates/example_config_terraform.yaml")
  vars = {
    demo_target_role_arn                               = aws_iam_role.consoleme_target.arn
    demo_app_role_arn_1                                = aws_iam_role.consoleme_example_app_role_1.arn
    demo_app_role_arn_2                                = aws_iam_role.consoleme_example_app_role_2.arn
    demo_user_role_arn_1                               = aws_iam_role.consoleme_example_user_role_1.arn
    demo_user_role_arn_2                               = aws_iam_role.consoleme_example_user_role_2.arn
    current_account_id                                 = data.aws_caller_identity.current.account_id
    sync_accounts_from_organizations                   = var.sync_accounts_from_organizations
    sync_accounts_from_organizations_master_account_id = var.sync_accounts_from_organizations_master_account_id != null ? var.sync_accounts_from_organizations_master_account_id : data.aws_caller_identity.current.account_id
    sync_accounts_from_organizations_role_to_assume    = var.sync_accounts_from_organizations_role_to_assume
  }
}

data "template_file" "consoleme_userdata" {
  template = file("${path.module}/templates/userdata.sh")
  vars = {
    bucket             = aws_s3_bucket.consoleme_source_bucket.bucket
    current_account_id = data.aws_caller_identity.current.account_id
    demo_config        = data.template_file.consoleme_config.rendered
    region             = data.aws_region.current.name
    CONFIG_LOCATION    = var.CONFIG_LOCATION
  }
}


