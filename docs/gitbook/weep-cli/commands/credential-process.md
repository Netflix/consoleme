---
description: Source Credentials from Weep automatically with Credential Process
---

# Credential Process



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

Then just run your application or AWS cli command with the appropriate `AWS_PROFILE` environment variable set:

```bash
AWS_PROFILE=test_account_user aws sts get-caller-identity
```

If you’re using the AWS cli, you can also pass `--profile` like this:

```bash
aws sts get-caller-identity --profile test_account_user
```

You can generate your `~/.aws/config` file with all of your eligible roles with the following command:

```bash
weep generate_credential_process_config
```

