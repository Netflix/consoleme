module "server" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-ec2-instance?ref=v2.16.0"

  name                        = module.compute_label.id
  instance_count              = 1
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  key_name                    = var.key_name
  iam_instance_profile        = aws_iam_instance_profile.ConsoleMeInstanceProfile.name
  subnet_id                   = module.network.private_subnets[0]
  user_data                   = data.template_file.consoleme_userdata.rendered

  root_block_device = [
    {
      volume_type = "gp2"
      volume_size = var.volume_size
      encrypted   = true
      kms_key_id  = module.kms_ebs.key_arn
    }
  ]

  metadata_options = {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
  }

  vpc_security_group_ids = [aws_security_group.external.id]

  tags = module.compute_label.tags
}

module "kms_ebs" {
  source                  = "git::https://github.com/cloudposse/terraform-aws-kms-key.git?ref=0.7.0"
  namespace               = var.namespace
  stage                   = var.stage
  name                    = var.name
  description             = "KMS key for ConsoleMe disk"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  alias                   = var.kms_key_alias
  tags                    = module.compute_label.tags
}

/**
  Creating a load balancer to "port forward" traffic from the Internet into the private instance.
  This is just another means of security, so the server with the keys to the kingdom is not sitting on a public network.
*/
resource "aws_lb" "public-to-private-lb" {
  name               = "public-to-private-lb"
  internal           = var.allow_internet_access ? false : true
  load_balancer_type = "network" // Using a network LB for HTTPS traffic because we just want to forward packets internally, nothing more
  subnets            = [module.network.private_subnets[0]]
}

resource "aws_lb_target_group" "consoleme-servers" {
  name     = "consoleme-servers"
  port     = 8081
  protocol = "TCP"
  vpc_id   = module.network.vpc_id
}

resource "aws_lb_target_group_attachment" "test" {
  target_group_arn = aws_lb_target_group.consoleme-servers.arn
  target_id        = module.server.id[0]
  port             = 8081
}

resource "aws_lb_listener" "public-8081" {
  load_balancer_arn = aws_lb.public-to-private-lb.arn
  port              = "8081"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.consoleme-servers.arn
  }
}
