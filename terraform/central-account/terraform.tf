provider "aws" {
  region  = var.region
}

provider "template" {
}

terraform {
  required_version = ">= 0.13.0"
}