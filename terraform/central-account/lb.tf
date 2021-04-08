
/**
  Creating a load balancer to "port forward" traffic from the Internet into the private instance.
  This does two things:
    1. Keeps the ConsoleMe server on a private network.
    2. Enables the use of ALB Authentication.
*/

resource "aws_lb" "public-to-private-lb" {
  name               = "consoleme-lb"
  internal           = var.allow_internet_access ? false : true
  load_balancer_type = "application"
  subnets            = module.network.public_subnets
  security_groups    = [aws_security_group.lb-sg.id]
}

resource "aws_lb_target_group" "consoleme-servers" {
  name     = "consoleme-servers"
  port     = 8081 # The port the server listens on
  protocol = "HTTP"
  vpc_id   = module.network.vpc_id
}

resource "aws_lb_target_group_attachment" "test" {
  target_group_arn = aws_lb_target_group.consoleme-servers.arn
  target_id        = module.server.id[0]
  port             = 8081
}


// Unauthenticated routes are used for the challenge authentication and credential retrieval flows on the command line.
resource "aws_lb_listener_rule" "unauthenticated-routes-1" {
  listener_arn = aws_lb_listener.public-8081.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.consoleme-servers.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/get_credentials*", "/api/v1/get_roles*", "/noauth/v1/challenge_generator/*",
      "/noauth/v1/challenge_poller/*", "/api/v2/mtls/roles/*"]
    }
  }
}

resource "aws_lb_listener_rule" "unauthenticated-routes-2" {
  listener_arn = aws_lb_listener.public-8081.arn
  priority     = 2

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.consoleme-servers.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/myheaders/?", "/api/v2/get_resource_url*"]
    }
  }
}

resource "aws_lb_listener" "public-8081" {
  load_balancer_arn = aws_lb.public-to-private-lb.arn
  port              = var.lb_port
  protocol          = "HTTPS"
  certificate_arn   = (var.lb-certificate-arn == "" ? aws_acm_certificate.lb-self-signed[0].arn : var.lb-certificate-arn)

  default_action {
    type = "authenticate-oidc"

    authenticate_oidc {
      authorization_endpoint = var.lb-authentication-authorization-endpoint
      client_id              = var.lb-authentication-client-id
      client_secret          = var.lb-authentication-client-secret
      issuer                 = var.lb-authentication-issuer
      token_endpoint         = var.lb-authentication-token-endpoint
      user_info_endpoint     = var.lb-authentication-user-info-endpoint
      scope                  = var.lb-authentication-scope
    }
  }

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.consoleme-servers.arn
  }
}
