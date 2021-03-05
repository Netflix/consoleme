# AWS Credentials in the CLI using Weep and ConsoleMe

Weep is a CLI utility for getting AWS credentials from ConsoleMe, serving them to your AWS CLI or SDKs, and \(in many cases\) caching and refreshing credentials automatically.

Read about the specifics in our [Getting Started with Weep](cli.md) guide.

Weep supports the following operations:

1\) **Emulate the ECS Credential Provider locally**. \(This provides a convenient way to get credentials on-demand, without needing networking rules. Each of your shells or IDEs can use a different role. Weep will cache these credentials and refresh them on demand\):

![](../.gitbook/assets/ecs.svg)

2\) **Emulate the EC2 Instance Metadata Service locally**:

![](../.gitbook/assets/weep_metadata.svg)

3\) **Invoke weep using the** [**credential\_process flow**](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sourcing-external.html)**.** \(Note: We've seen this introduce performance issues when you have a large number of roles.\)

![](../.gitbook/assets/weep_credential_provider.svg)

4\) **Export credentials as environment variables**

![](../.gitbook/assets/weep_env_variable%20%281%29.svg)

5\) **Write credentials to your ~/.aws/credentials file**

![](../.gitbook/assets/weep_file%20%281%29.svg)

6\) **Have weep perform nested assume-role calls on your behalf, and serve the assumed role credentials** \(The video below shows this flow for Weep's ECS credential provider mode. You can do this with most other modes as well\):

![](../.gitbook/assets/weep-ecs-assume-role.svg)

