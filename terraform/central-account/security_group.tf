resource "aws_security_group" "server" {
  vpc_id      = module.network.vpc_id
  name        = module.security_group_label.id
  description = "Allow ingress from authorized IPs to self, and egress to everywhere."
  tags        = module.security_group_label.tags
}

resource "aws_security_group_rule" "internal_ingress_all_self" {
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.server.id
  to_port           = 0
  type              = "ingress"
  cidr_blocks       = [var.vpc_cidr]
}

# HTTPS
resource "aws_security_group_rule" "external_ingress_8081" {
  from_port         = 8081
  protocol          = "tcp"
  security_group_id = aws_security_group.server.id
  to_port           = 8081
  type              = "ingress"
  cidr_blocks       = var.allowed_inbound_cidr_blocks
}

# SSH
resource "aws_security_group_rule" "external_ingress_ssh" {
  count             = var.associate_public_ip_address_to_ec2 ? 1 : 0
  from_port         = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.server.id
  to_port           = 22
  type              = "ingress"
  cidr_blocks       = var.allowed_inbound_cidr_blocks
}

resource "aws_security_group_rule" "external_egress_allow_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  security_group_id = aws_security_group.server.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# For the public load balancer
resource "aws_security_group" "lb-sg" {
  name        = "allow_access_to_consoleme"
  description = "Allows access to the load balancer, which forwards to the ConsoleMe server."
  vpc_id      = module.network.vpc_id

  ingress {
    description = "HTTPS for accessing ConsoleMe"
    from_port   = var.lb_port
    to_port     = var.lb_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_inbound_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_access_to_consoleme"
  }
}
