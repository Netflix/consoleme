data "aws_caller_identity" "current" {}

data "aws_ami" "amazon_linux" {
  most_recent = true

  filter {
    name   = "name"
    values = [var.ec2_ami_name_filter]
  }

  owners = [var.ec2_ami_owner_filter]
}

data "template_file" "consoleme_userdata" {
  template = file("${path.module}/templates/userdata.sh")
  vars = {
    bucket = var.bucket
    current_account_id = data.aws_caller_identity.current.account_id
  }
}
