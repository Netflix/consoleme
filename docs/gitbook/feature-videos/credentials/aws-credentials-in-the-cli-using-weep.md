# AWS Credentials in the CLI using Weep

Weep is a CLI utility for getting AWS credentials from ConsoleMe, serving them to your AWS CLI or SDKs, and \(in many case\) caching/refreshing credentials automatically.

 Read about the specifics in our [Getting Started with Weep](../../cli.md) guide. 

Weep supports the following operations:

1\) **Emulating the ECS Credential Provider locally**. \(This provides a convenient way to get credentials on-demand, without needing networking rules. Each of your shells or IDEs can use a different role. Weep will cache these credentials and refresh them on demand\):

{% embed url="https://www.youtube.com/watch?v=lNYgK-IBQgY" %}

2\) **Emulating the EC2 Instance Metadata Service locally**:

{% embed url="https://www.youtube.com/watch?v=QfXDdUuFYmA" %}

3\) Invoking weep using the [credential\_process flow](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sourcing-external.html). \(Note: We've seen this introduce performance issues for a large number of roles.\)

![](../../.gitbook/assets/weep_credential_provider.svg)

4\) Exporting credentials as environment variables

![](../../.gitbook/assets/weep_env_variable.svg)

5\) Exporting credentials to your ~/.aws/credentials file

![](../../.gitbook/assets/weep_file.svg)

