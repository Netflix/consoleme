
resource "aws_security_group" "external" {
  vpc_id      = module.network.vpc_id
  name        = module.security_group_label.id
  description = "Allow ingress from authorized IPs to self, and egress to everywhere."
  tags        = module.security_group_label.tags
}


resource "aws_security_group_rule" "internal_ingress_all_self" {
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.external.id
  to_port           = 0
  type              = "ingress"
  cidr_blocks       = [var.vpc_cidr]
}

resource "aws_security_group_rule" "external_ingress_ssh" {
  from_port         = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.external.id
  to_port           = 22
  cidr_blocks       = var.allowed_inbound_cidr_blocks
  type              = "ingress"
}

resource "aws_security_group_rule" "external_ingress_443" {
  from_port         = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.external.id
  to_port           = 443
  type              = "ingress"
  cidr_blocks       = var.allowed_inbound_cidr_blocks
}

# HTTPS
resource "aws_security_group_rule" "external_ingress_7473" {
  from_port         = 8081
  protocol          = "tcp"
  security_group_id = aws_security_group.external.id
  to_port           = 8081
  type              = "ingress"
  cidr_blocks       = var.allowed_inbound_cidr_blocks
}

resource "aws_security_group_rule" "external_egress_allow_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  security_group_id = aws_security_group.external.id
  cidr_blocks       = ["0.0.0.0/0"]
}

