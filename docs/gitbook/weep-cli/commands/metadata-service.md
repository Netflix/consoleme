---
description: Start a metadata service hosting STS credentials for your role requested
---

# Metadata Service

{% hint style="warning" %}
You must NOT have a shared credentials file \(`~/.aws/credentials`\) when running the metadata service or your AWS SDK will favor that first. You should also not have environment variables set for `AWS_ACCESS_KEY`. These checks will come in a future update. See the [AWS Credential Provider Chain](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/credentials.html#credentials-default) for more details.
{% endhint %}

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

{% hint style="info" %}
You will need to set up routing. Instructions can be found in [Advanced Configuration](../advanced-configuration/#setup-routing-for-metadata-proxy).
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

