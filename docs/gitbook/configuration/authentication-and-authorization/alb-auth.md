# ALB Auth

ConsoleMe can be configured behind an ALB with authentication enabled, and it can validate the JWT to retrieve the authenticated user and their groups. . We have an example configuration [here](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_alb_auth.yaml).

The settings that must be defined for the ALB Auth flow to work are as follows:

```text
auth:
  get_user_by_aws_alb_auth: true
  set_auth_cookie: true

get_user_by_aws_alb_auth_settings:
  jwt_email_key: sub
  jwt_groups_key: groups
```

