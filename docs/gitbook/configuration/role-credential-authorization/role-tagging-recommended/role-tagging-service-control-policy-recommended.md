# Role Tagging Service Control Policy \(Recommended\)

We highly recommend that you prevent unauthorized services from modifying sensitive tags. In order to do this, we recommend using an organizational-wide Service Control Policy \(SCP\).

1. Log in to your AWS Organizations master account and create an SCP
2. Configure it with a policy similar to the one below. Be sure to rename **sensitivetagprefix-** to whatever you've decided as a tag prefix. Also ensure that the Principal ARNs match what your ConsoleMe Spoke account roles are named. Add any administrative or fallback users that will need to also perform tagging.
3. Attach this policy to all of your accounts. Use discretion and roll it out slowly if you're concerned about breakage.

```text
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "protectmytags",
            "Effect": "Deny",
            "Action": [
                "iam:CreateRole",
                "iam:TagRole",
                "iam:UntagRole",
                "iam:CreateUser",
                "iam:TagUser",
                "iam:UntagUser"
            ],
            "Resource": [
                "*"
            ],
            "Condition": {
                "ForAnyValue:StringLike": {
                    "aws:TagKeys": [
                        "sensitivetagprefix-*"
                    ]
                },
                "StringNotLike": {
                    "aws:PrincipalArn": [
                        "arn:aws:iam::*:role/ConsoleMe"
                    ]
                }
            }
        }
    ]
}
```

