---
description: HTTP server used to retrieve credentials from Weep automatically
---

# Serve

Weep supports emulating the [EC2 Instance Metadata Service \(IMDS\)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html) and the [ECS credential provider](https://docs.aws.amazon.com/AWSJavaSDK/latest/javadoc/com/amazonaws/auth/EC2ContainerCredentialsProviderWrapper.html) to provide credentials to your AWS SDK. This is the recommended way to use Weep for the best experience.

This solution can be minimally configured by setting the `AWS_CONTAINER_CREDENTIALS_FULL_URI` environment variable for your shell or process. There's no need for iptables or routing rules with this approach, and each different shell or process can use weep to request credentials for different roles. Weep will cache the credentials you request in-memory, and will refresh them on-demand when they are within 10 minutes of expiring.

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

In one shell, run weep:

```bash
weep serve
```

In your favorite IDE or shell, set the `AWS_CONTAINER_CREDENTIALS_FULL_URI` environment variable and run AWS commands. The environment variable's value is structured like this:

```bash
AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/consoleme_oss_1
                                          ▔▔▔▔▔▔▔▔▔ ▔▔▔▔     ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
                                          │         │        └─ Role name/search string
                                          │         └─ Weep port (probably 9091)
                                          └─ Weep hostname (probably localhost)
```

```bash
AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/consoleme_oss_1 aws sts get-caller-identity
{
   "UserId": "AROA4JEFLERSKVPFT4INI:user@example.com",
   "Account": "123456789012",
   "Arn": "arn:aws:sts::123456789012:assumed-role/consoleme_oss_1_test_user/user@example.com"
}

AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/consoleme_oss_2 aws sts get-caller-identity
{
   "UserId": "AROA6KW3MOV2F7J6AT4PC:user@example.com",
   "Account": "223456789012",
   "Arn": "arn:aws:sts::223456789012:assumed-role/consoleme_oss_2_test_user/user@example.com"
}
```

Configure this environment variable in your IDE for full effect.

### IMDS Emulation

This is a more advanced feature. It's more involved to get set up, but it lets you avoid setting an environment variable to use Weep.

{% hint style="warning" %}
AWS SDKs expect IMDS to be served at `http://169.254.169.254`. You will need to set up routing for this functionality to work. Instructions can be found in [Advanced Configuration](../advanced-configuration/#setup-routing-for-metadata-proxy).
{% endhint %}

To serve the IMDS endpoints, use the `serve` command along with a role identifier or search string:

```bash
weep serve arn:aws:iam::012345678901:role/coolApp
INFO[0000] Starting weep meta-data service...
INFO[0000] Server started on: 127.0.0.1:9090

curl http://169.254.169.254/latest/meta-data/iam/security-credentials/coolApp
{
  "Code": "Success",
  "LastUpdated": "2018-08-01T15:26:14Z",
  "Type": "AWS-HMAC",
  "AccessKeyId": "ASIA
...
```

