---
description: Start a metadata service hosting STS credentials for your role requested
---

# Metadata Service

The Weep metadata service command starts an HTTP server that emulates the [EC2 Instance Metadata Service \(IMDS\)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html). When using this feature, credentials are automatically refreshed by making more calls to the service.

{% hint style="warning" %}
AWS SDKs expect IMDS to be served at `http://169.254.169.254`. You will need to set up routing for this functionality to work. Instructions can be found in [Advanced Configuration](../advanced-configuration/#setup-routing-for-metadata-proxy).
{% endhint %}

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

```bash
weep metadata arn:aws:iam::012345678901:role/coolApp
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

