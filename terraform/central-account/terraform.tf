provider "aws" {
  region  = var.region
  version = ">= 3"
}

provider "template" {
  version = "~> 2.1"
}

terraform {
  required_version = ">= 0.13.0"
}