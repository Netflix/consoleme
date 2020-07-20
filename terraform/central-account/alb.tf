module "alb" {
  source = "terraform-aws-modules/alb/aws"
  version = "~> 5.0"

  name = "consoleme-alb"

  load_balancer_type = "application"

  vpc_id = module.network.vpc_id
  subnets = module.network.public_subnets
  security_groups = [
    aws_security_group.alb.id]

  target_groups = aws_lb_target_group.consoleme-web.id

  https_listeners = [
    {
      port = 80
      protocol = "HTTP"
      action_type = "redirect"
      redirect = {
        port = "443"
        protocol = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  ]

// A formal deploy should auto-redirect 80 -> 443 with the following settings:
//  http_tcp_listeners = [
//    {
//      port = 80
//      protocol = "HTTP"
//      action_type = "redirect"
//      redirect = {
//        port = "443"
//        protocol = "HTTPS"
//        status_code = "HTTP_301"
//      }
//    }
//  ]
}

resource "aws_lb_target_group" "consoleme-web" {
  name     = "consoleme-web"
  port     = 8081
  protocol = "HTTP"
  vpc_id   = module.network.vpc_id
}

resource "aws_lb_target_group_attachment" "consoleme-web" {
  target_group_arn = aws_lb_target_group.consoleme-web.arn
  target_id        = module.server.id[0]
  port             = 8081
}
