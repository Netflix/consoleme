---
description: Write to your ~/.aws/credentials file
---

# File

Weep can write credentials to the [AWS shared credential](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) file in your home directory. The AWS CLI and SDKs will refer to this file and use the credentials for a specified profile \(or `default` if none is specified\).

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

Then just run your application or AWS CLI command with the appropriate profile:

```bash
AWS_PROFILE=test_account_user aws sts get-caller-identity

# you can also use the --profile flag
aws --profile test_account_user sts get-caller-identity
```

Profiles can also be set in AWS SDKs. For example in `boto3`:

```python
import boto3

session = boto3.Session(profile_name="test_account_user")
client = session.client("sts")
print(client.get_caller_identity())
```

