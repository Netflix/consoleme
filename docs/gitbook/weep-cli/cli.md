---
description: "Using Weep, the ConsoleMe CLI"
---

# Getting Started with Weep

Weep is a CLI tool that makes it easy to use credentials from ConsoleMe for local development.

Weep offers five methods to serve credentials:

1. Local [ECS credential provider](https://docs.aws.amazon.com/AWSJavaSDK/latest/javadoc/com/amazonaws/auth/EC2ContainerCredentialsProviderWrapper.html)
2. Local [Meta-data service](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)
3. Source credentials with [credential_process](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sourcing-external.html)
4. Export credentials to [environment variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)
5. Write credentials to [file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

{% hint style="success" %}
Read about [AWS configuration settings and precedence](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html#cli-configure-quickstart-precedence) for information about precedence of credential sources.
{% endhint %}

## Installation

Binaries can be downloaded from the GitHub release page: [https://github.com/Netflix/weep/releases/latest](https://github.com/Netflix/weep/releases/latest)

Download the correct binary for your platform and place it in your path.

## Usage

### Print Defaults

```text
Weep is a CLI tool that manages AWS access via ConsoleMe for local development.

Usage:
  weep [command]

Available Commands:
  completion                         Generate completion script
  credential_process                 Retrieve credentials and writes them in credential_process format
  ecs_credential_provider            Run a local ECS Credential Provider endpoint that serves and caches credentials for roles on demand
  export                             Retrieve credentials to be exported as environment variables
  file                               Retrieve credentials and save them to a credentials file
  generate_credential_process_config Write all of your eligible roles as profiles in your AWS Config to source credentials from Weep
  help                               Help about any command
  list                               List available roles
  metadata                           Run a local Instance Metadata Service (IMDS) endpoint that serves credentials
  setup                              Print setup information
  version                            Print version information

Flags:
  -A, --assume-role strings   one or more roles to assume after retrieving credentials
  -c, --config string         config file (default is $HOME/.weep.yaml)
  -h, --help                  help for weep
      --log-format string     log format (json or tty)
      --log-level string      log level (debug, info, warn)

Use "weep [command] --help" for more information about a command.
```
