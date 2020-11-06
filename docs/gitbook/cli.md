# Weep CLI

{% hint style="warning" %}
You must NOT have a `~/.aws/credentials` file when running --meta-data or your SDK will favor that FIRST. You should also not have environmental variables set for `AWS_ACCESS_KEY`. These checks will come in a future update. See the [AWS Credential Provider Chain](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/credentials.html#credentials-default) for more details.
{% endhint %}

Weep offers five methods to serve credentials:

1. Local [ECS credential provider](https://docs.aws.amazon.com/AWSJavaSDK/latest/javadoc/com/amazonaws/auth/EC2ContainerCredentialsProviderWrapper.html)
2. Local [Meta-data service](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)
3. Source credentials with [credential\_process](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sourcing-external.html)
4. Export credentials to [environment variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)
5. Write credentials to [file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

## Installation

Binaries can be downloaded from the GitHub release page: [https://github.com/Netflix/weep/releases/latest](https://github.com/Netflix/weep/releases/latest)

Download the correct binary for your platform and place it in your path.

## Usage

### Print Defaults

```text
Available Commands:

  credential_process Retrieve credentials and writes them in credential_process format
  export             Retrieve credentials to be exported as environment variables
  file               retrieve credentials and save them to a credentials file
  help               Help about any command
  list               List available roles
  metadata           Run a local Instance Metadata Service (IMDS) endpoint that serves credentials
  setup              Print setup information for Weep
  version            Print the version number of Weep
```

### Get all eligible roles

```bash
weep list
Roles:
   arn:aws:iam::012345678901:role/admin
   arn:aws:iam::112345678901:role/poweruser
   arn:aws:iam::212345678901:role/readonly
   arn:aws:iam::312345678901:role/admin
...
```

### Sourcing Credentials from Weep Automatically with the ECS Credential Provider feature

[Here’s a demo of ECS Credential Provider mode.](https://youtu.be/lNYgK-IBQgY)

Weep supports emulating the ECS credential provider to provide credentials to your AWS SDK. This is the recommended way to use Weep for the best experience.

This solution can be minimally configured by setting the `AWS_CONTAINER_CREDENTIALS_FULL_URI` environment variable for your shell or process. There's no need for iptables or routing rules with this approach, and each different shell or process can use weep to request credentials for different roles. Weep will cache the credentials you request in-memory, and will refresh them on-demand when they are within 10 minutes of expiring.

In one shell, run weep:

```bash
weep ecs_credential_provider
```

In your favorite IDE or shell, set the `AWS_CONTAINER_CREDENTIALS_FULL_URI` environment variable and run AWS commands.

```bash
AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9090/ecs/consoleme_oss_1 aws sts get-caller-identity
{
   "UserId": "AROA4JEFLERSKVPFT4INI:user@example.com",
   "Account": "123456789012",
   "Arn": "arn:aws:sts::123456789012:assumed-role/consoleme_oss_1_test_user/user@example.com"
}

AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9090/ecs/consoleme_oss_2 aws sts get-caller-identity
{
   "UserId": "AROA6KW3MOV2F7J6AT4PC:user@example.com",
   "Account": "223456789012",
   "Arn": "arn:aws:sts::223456789012:assumed-role/consoleme_oss_2_test_user/user@example.com"
}
```

Configure this in your IDE for full effect.

### Start a metadata service hosting STS credentials for your role requested

[Here’s a demo of metadata service mode.](https://youtu.be/4sK5JHwgjjg)

!!! note You will need to set up routing. Instructions are below.

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

### Source Credentials from Weep automatically with Credential Process

[Here’s a demo of credential process mode.](https://www.youtube.com/watch?v=4sK5JHwgjjg)

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

### Export credentials

```bash
weep export arn:aws:iam::012345678901:role/coolApp
INFO[0001] Successfully retrieved credentials.  Expire: 2018-08-01 15:39:12 -0700 PDT
export AWS_ACCESS_KEY_ID=ASIAS...
```

### Write to your ~/.aws/credentials file

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

### Setup Routing for Metadata Proxy

We highly recommend you check out the ECS credential provider emulator capability instead of using this. But if needed, here are the steps:

{% tabs %}
{% tab title="Mac" %}
Run commands:

```bash
sudo ifconfig lo0 169.254.169.254 alias

echo "rdr pass on lo0 inet proto tcp from any to 169.254.169.254 port 80 -> 127.0.0.1 port 9090" | sudo pfctl -ef -
```

Alternatively to persist the settings above on a Mac, [download the plists](https://drive.google.com/drive/folders/1Z038jaI1e21t48f94bfCwAjDazYQjTNd) and place them in `/Library/LaunchDaemons` and reboot or issue the following commands:

```bash
launchctl load /Library/LaunchDaemons/com.user.weep.plist
launchctl load /Library/LaunchDaemons/com.user.lo0-loopback.plist
```
{% endtab %}

{% tab title="Linux" %}
Create a txt file at the location of your choosing with the following contents:

```text
*nat
:PREROUTING ACCEPT [0:0]
:INPUT ACCEPT [0:0]
:OUTPUT ACCEPT [1:216]
:POSTROUTING ACCEPT [1:216]
-A OUTPUT -d 169.254.169.254/32 -p tcp -m tcp --dport 80 -j DNAT --to-destination 127.0.0.1:9090
COMMIT
```

Enable the rules by running the following:

```text
sudo /sbin/iptables-restore < <path_to_file>.txt
```
{% endtab %}
{% endtabs %}

