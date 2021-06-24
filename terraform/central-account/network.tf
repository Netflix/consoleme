module "network" {
  source = "github.com/terraform-aws-modules/terraform-aws-vpc?ref=v2.77.0"

  name = module.network_label.id
  cidr = var.vpc_cidr
  azs  = var.subnet_azs

  enable_nat_gateway                 = true
  enable_vpn_gateway                 = true
  propagate_public_route_tables_vgw  = true
  propagate_private_route_tables_vgw = true
  create_database_subnet_group       = false
  enable_dhcp_options                = true
  enable_dns_hostnames               = true
  enable_dns_support                 = true
  enable_s3_endpoint                 = true
  enable_dynamodb_endpoint           = true
  tags                               = var.default_tags
  create_vpc                         = true
  public_subnet_suffix               = "public-subnet"
  public_subnets                     = var.public_subnet_cidrs
  private_subnet_suffix              = "private-subnet"
  private_subnets                    = var.private_subnet_cidrs
}