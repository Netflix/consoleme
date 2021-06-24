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
