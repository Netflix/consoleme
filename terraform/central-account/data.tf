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
    demo_target_role_arn = aws_iam_role.consoleme_target.arn
    current_account_id = data.aws_caller_identity.current.account_id
  }
}

data "template_file" "consoleme_userdata" {
  template = file("${path.module}/templates/userdata.sh")
  vars = {
    bucket = var.bucket
    current_account_id = data.aws_caller_identity.current.account_id
    demo_config = data.template_file.consoleme_config.rendered
    region = data.aws_region.current.name
    CONFIG_LOCATION = var.CONFIG_LOCATION
  }
}


