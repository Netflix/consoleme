module "server" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-ec2-instance?ref=v2.16.0"

  name                 = module.compute_label.id
  instance_count       = 1
  ami                  = data.aws_ami.amazon_linux.id
  instance_type        = var.instance_type
  key_name             = var.key_name
  iam_instance_profile = aws_iam_instance_profile.ConsoleMeInstanceProfile.name
  subnet_id            = module.network.private_subnets[0]
  user_data = templatefile("${path.module}/templates/userdata.sh", tomap({
    bucket                  = aws_s3_bucket.consoleme_files_bucket.bucket
    current_account_id      = data.aws_caller_identity.current.account_id
    region                  = data.aws_region.current.name
    CONFIG_LOCATION         = "/apps/consoleme/example_config/example_config_terraform.yaml"
    CONSOLEME_CONFIG_S3     = format("s3://%s/%s", aws_s3_bucket.consoleme_files_bucket.id, aws_s3_bucket_object.consoleme_config.id)
    custom_user_data_script = var.custom_user_data_script
    consoleme_repo          = var.consoleme_repo
  }))

  root_block_device = [
    {
      volume_type = "gp2"
      volume_size = var.volume_size
      encrypted   = true
      kms_key_id  = module.kms_ebs.key_arn
    }
  ]

  metadata_options = {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  vpc_security_group_ids = [aws_security_group.server.id]

  tags = module.compute_label.tags

  depends_on = [aws_s3_bucket_object.consoleme_config]
}

module "kms_ebs" {
  source                  = "git::https://github.com/cloudposse/terraform-aws-kms-key.git?ref=0.10.0"
  namespace               = var.namespace
  stage                   = var.stage
  name                    = var.name
  description             = "KMS key for ConsoleMe disk"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  alias                   = var.kms_key_alias
  tags                    = module.compute_label.tags
}
