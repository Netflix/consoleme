provider "aws" {
  region = var.region
}

terraform {
  required_providers {
    aws = {
      version = ">= 3"
    }
  }
  required_version = ">= 0.13.0"
  // Unfortunately, we can't use variables to specify a backend S3 bucket / DynamoDB table for Terraform state
  // consistency. If you want to make use of this, you'll need to make a copy of these terraform files in your own
  // private repository, and customize as necessary
  //  backend "s3" {
  //    bucket         = "your-terraform-state-bucket"
  //    key            = "terraform/terraform.tfstate"
  //    region         = "your-region"
  //    dynamodb_table = "your-terraform-state-dynamodb-table"
  //  }
}
