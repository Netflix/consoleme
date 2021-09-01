# ALB Auth \(Recommended\)

ConsoleMe can be configured behind an ALB with authentication enabled, and it can validate the JWT to retrieve the authenticated user and their groups. We have an example configuration [here](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_alb_auth.yaml).

The settings that must be defined for the ALB Auth flow to work are as follows:

```text
auth:
  get_user_by_aws_alb_auth: true
  set_auth_cookie: true

get_user_by_aws_alb_auth_settings:
  jwt_email_key: sub
  jwt_groups_key: groups
```

Prerequisites:

* A Route53 hosted zone that will contain your ConsoleMe domain
* An EC2 target group with one or more ConsoleMe instances or containers
* ConsoleMe \(And Celery\) should be running with the `EC2_REGION` environment variable set to the region your instance\(s\) are in. For example: `EC2_REGION=us-west-2`.

Steps:

1. Create an Application Load Balancer in AWS with your desired settings. 

![](../../.gitbook/assets/image%20%2828%29.png)

2. Create or use a TLS certificate for your domain \(ACM is recommended for auto-renewal\). Choose your [ELB Security Policy](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/create-tls-listener.html) based on your company's paranoia level.

![](../../.gitbook/assets/image%20%2819%29.png)

3. Create a Security Group to define which IP ranges or security groups can reach your ConsoleMe load balancer. In our case, ConsoleMe is public and we're opening it up to everyone. 

![](../../.gitbook/assets/image%20%2824%29.png)

4. Create or use a target group for your ConsoleMe instances/containers. By default, ConsoleMe listens on HTTP port 8081, and returns healthcheck queries on the `/healthcheck` endpoint.

![](../../.gitbook/assets/image%20%2822%29.png)

5. Register targets \(Or skip for now\), and create your load balancer.

6. In the EC2 console, modify your **Port 80 listener** \(Load Balancers &gt; \(Select your newly created load balancer\) &gt; Listeners -&gt; **Port 80**. Configure the default action to route traffic from port 80 to port 443.

![](../../.gitbook/assets/image%20%2821%29.png)

7. Modify your **Port 443 listener.** The first step should authenticate against Cognito, or your OIDC identity provider. The next step is to forward to your ConsoleMe target group. Here are a few examples:

* Google \(Scopes required: **openid email** \)

![](../../.gitbook/assets/image%20%2836%29%20%283%29%20%283%29%20%283%29%20%282%29.png)

* Cognito  \(Scopes required: **openid**\)

![](../../.gitbook/assets/image%20%2834%29.png)

* Okta \(Scopes required: **openid email groups**\)

![](../../.gitbook/assets/image%20%2830%29.png)

8. The rule after your Authenticate rule should forward to your ConsoleMe target group.

![](../../.gitbook/assets/image%20%2835%29.png)

8. Set up rules on your load balancer to exclude the following endpoints from ALB Authentication. These endpoints are used to perform CLI authentication and actions. 

Note: Only 5 conditions are allowed per rule, so you'll need two rules to exclude the following domains from authentication, and a third default rule to perform the default authenticate/forward action.

* /noauth/v1/challenge\_poller/\*
* /noauth/v1/challenge\_generator/\*
* /api/v1/get\_roles\*
* /api/v2/mtls/roles/\*
* /api/v1/get\_credentials\*
* /api/v1/myheaders/?
* /api/v2/get\_resource\_url\*

![](../../.gitbook/assets/image%20%2823%29.png)

9. Create a ConsoleMe configuration to support your ALB Authentication experience, and deploy ConsoleMe to your target group with this configuration. When a user authenticates, ConsoleMe will receive and decode two headers sent from the ALB. The first is "X-Amzn-Oidc-Data", which contains the user's identity and claims. The second includes an access token from the identity provider. ConsoleMe will attempt to decode the access token and retrieve the user's group memberships based on its configuration. 

