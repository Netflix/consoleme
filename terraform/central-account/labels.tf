module "network_label" {
  source       = "git::https://github.com/cloudposse/terraform-terraform-label.git?ref=0.8.0"
  namespace    = var.namespace
  stage        = var.stage
  name         = var.name
  delimiter    = var.delimiter
  convert_case = var.convert_case
  tags         = var.default_tags
  enabled      = "true"
}

module "security_group_label" {
  source       = "git::https://github.com/cloudposse/terraform-terraform-label.git?ref=0.8.0"
  namespace    = var.namespace
  stage        = var.stage
  name         = var.name
  attributes   = ["sg"]
  delimiter    = var.delimiter
  convert_case = var.convert_case
  tags         = var.default_tags
  enabled      = "true"
}

module "compute_label" {
  source       = "git::https://github.com/cloudposse/terraform-terraform-label.git?ref=0.8.0"
  namespace    = var.namespace
  stage        = var.stage
  name         = var.name
  delimiter    = var.delimiter
  convert_case = var.convert_case
  tags         = var.default_tags
  enabled      = "true"
}