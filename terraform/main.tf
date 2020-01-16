provider "aws" {
  region     = "us-west-2"
}

resource "aws_vpc" "consoleme" {
	cidr_block = "10.0.0.0/16"
	enable_dns_hostnames = true
	enable_dns_support = true
	tags = {
		Name="consoleme-vpc"
	}
}

resource "aws_subnet" "consoleme_subnet" {
	cidr_block = cidrsubnet(aws_vpc.consoleme.cidr_block, 3, 1)
	vpc_id = aws_vpc.consoleme.id
	availability_zone = "us-west-2a"
}

resource "aws_instance" "example" {
  ami           = "ami-2757f631"
  instance_type = "t2.micro"
}