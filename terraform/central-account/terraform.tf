provider "aws" {
  region  = var.region
  version = "~> 2.53"
}

provider "template" {
  version = "~> 2.1"
}