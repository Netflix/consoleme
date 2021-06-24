---
description: Source Credentials from Weep automatically with Credential Process
---

# Credential Process

AWS SDKs have the ability to source credentials from an external process by specifying a command in your AWS config file. You can read more about this feature in the [AWS docs](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sourcing-external.html).

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

Update your `~/.aws/config` file with information about the profile you want to configure, and the role you want weep to assume. Example:

```text
[profile consoleme_oss_1]
credential_process = weep credential_process arn:aws:iam::012345678901:role/consoleme_oss_1_test_admin

[profile consoleme_oss_2]
credential_process = weep credential_process consoleme_oss_2_test_admin

[profile test_account_user]
credential_process = weep credential_process test_account_user
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

## Generating Credential Process Commands

Weep can automatically update your AWS config file with profiles for each of your available roles. These profiles are named with the full ARN of the role.

{% hint style="danger" %}
AWS SDKs appear to be analyzing your `~/.aws/config` file on each API call. This could drastically slow you down if your the file is too large.
{% endhint %}

```bash
# Please read the caveat above before running this command. The size of your ~/.aws/config file may negatively impact
# the rate of your AWS API calls.
weep credential_process --generate
```

