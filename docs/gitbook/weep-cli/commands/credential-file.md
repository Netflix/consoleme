---
description: Write to your ~/.aws/credentials file
---

# Credential File

Weep can write credentials to the [AWS shared credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) file in your home directory. The AWS CLI and SDKs will refer to this file and use the credentials for a specified profile \(or `default` if none is specified\).

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

```bash
weep file test_account_user --profile default
```

This will write credentials to your `~/.aws/credentials` file that will be used automatically.

```bash
cat ~/.aws/credentials
```

```text
[default]
aws_access_key_id = ASIA4JEFLERSJZDM7YOH
aws_secret_access_key = .....
aws_session_token = .....
```

