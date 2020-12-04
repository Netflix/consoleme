# Credential Provider

### Sourcing Credentials from Weep Automatically with the ECS Credential Provider feature

Weep supports emulating the ECS credential provider to provide credentials to your AWS SDK. This is the recommended way to use Weep for the best experience.

This solution can be minimally configured by setting the `AWS_CONTAINER_CREDENTIALS_FULL_URI` environment variable for your shell or process. There's no need for iptables or routing rules with this approach, and each different shell or process can use weep to request credentials for different roles. Weep will cache the credentials you request in-memory, and will refresh them on-demand when they are within 10 minutes of expiring.

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

In one shell, run weep:

```bash
weep ecs_credential_provider
```

In your favorite IDE or shell, set the `AWS_CONTAINER_CREDENTIALS_FULL_URI` environment variable and run AWS commands.

```bash
AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9090/ecs/consoleme_oss_1 aws sts get-caller-identity
{
   "UserId": "AROA4JEFLERSKVPFT4INI:user@example.com",
   "Account": "123456789012",
   "Arn": "arn:aws:sts::123456789012:assumed-role/consoleme_oss_1_test_user/user@example.com"
}

AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9090/ecs/consoleme_oss_2 aws sts get-caller-identity
{
   "UserId": "AROA6KW3MOV2F7J6AT4PC:user@example.com",
   "Account": "223456789012",
   "Arn": "arn:aws:sts::223456789012:assumed-role/consoleme_oss_2_test_user/user@example.com"
}
```

Configure this in your IDE for full effect.

### 

