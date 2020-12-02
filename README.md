[![Discord](https://img.shields.io/discord/730908778299523072?label=Discord&logo=discord&style=flat-square)](https://discord.gg/tZ8S7Yg)

# ConsoleMe

ConsoleMe strives to be a multi-account AWS swiss-army knife, making AWS easier for your end-users and cloud administrators.
It is designed to consolidate the management of multiple accounts into a single web interface. It allows your end-users
and administrators to get credentials / console access to your different accounts, depending on their authorization
level. It provides mechanisms for end-users and administrators to both request and manage permissions for IAM roles,
S3 buckets, SQS queues, and SNS topics. A self-service wizard is also provided to guide users into requesting the
permissions they desire.

ConsoleMe is extensible and pluggable. We offer a set of basic plugins for authenticating users, determining their
groups and eligible roles, and more through the use of default plugins (consoleme/default_plugins).
If you need to link ConsoleMe with internal business logic, we recommend creating a new private repository
based on the default_plugins directory and modifying the code as appropriate to handle that custom internal logic.

ConsoleMe uses [Celery](https://github.com/celery/celery/) to run tasks on a schedule or on-demand. Our implementation
is also extensible through the usage of Python entry points. This means that you can also implement internal-only
Celery tasks to handle some of your custom business logic if needed.

The celery tasks in this repo are generally used to cache resources across your AWS accounts (such as IAM roles),
and report Celery metrics. We have tasks that perform the following:

- Cache IAM roles, SQS queues, SNS topics, and S3 buckets to Redis/DDB
- Report Celery Last Success Metrics (Used for alerting on failed tasks)
- Cache Cloudtrail Errors by ARN (This requires an internal celery task to aggregate Cloudtrail errors from your
  preferred source)

Netflix's internal celery tasks handle a variety of additional requirements that you may
be interested in implementing. These include:

- Caching S3/Cloudtrail errors from our Hive / ElasticSearch databases. We expose these to end-users in ConsoleMe
- Generating tags for our resources, which include the creator and owner of the resource, and any associated applications.
- Generating an IAM managed policy unique for each account which (when attached to a role) prevents the usage of an IAM
  role credential outside of the account. (This is used as a general credential theft and SSRF protection)
- Cache Google Groups, Users and Account Settings from internal services at Netflix

## Quick Start

Docker-Compose is the quickest way to get ConsoleMe up and running locally for testing purposes.
For development, we highly recommend setting up ConsoleMe locally with the instructions below this Quick Start.

BEFORE RUNNING THE COMMAND BELOW: We highly recommend that you put valid AWS credentials in your
[~/.aws/credentials file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-where),
using the default profile.

The role you use should have the permissions outlined under the `ConsoleMeInstanceProfile configuration` section below ([link](#consolemeinstanceprofile-configuration)). When you start the containers, it will attempt to populate your redis cache with live resources from your account.

```bash
# Ensure that you have valid AWS Credentials in your ~/.aws/credentials file under your `default` profile
# before running this command
docker-compose -f docker-compose.yaml -f docker-compose-dependencies.yaml up -d
```

After this is done, visit `http://localhost:3000`. You may notice the page is rather empty. One of the containers we
started should be initializing your redis cache with your AWS account resources, so you may need to give it a moment.
To follow along with resource caching, run the following docker command:

```bash
docker container logs -f consoleme-celery
```

By default, you're running ConsoleMe as an administrator with the local
[Docker development configuration](example_config/example_config_docker_development.yaml).

## Build and Run Instructions

ConsoleMe requires Python 3.8 or above. Crude installation instructions are below. This documentation is in dire need
of improvement.

### MacOS

```bash
# Install Python, Yarn, libxmlsec1, and other dependencies
brew install python@3.8 yarn pkgconfig libxmlsec1

# XCode Command-Line Tools
xcode-select --install

```

### Linux

Ubuntu disco/19.04+, Debian buster/10+

```bash
# Additional dependencies
apt-get install build-essential libxml2-dev libxmlsec1 libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev -y
```

#### Clone the ConsoleMe repo

```bash
git clone git@github.com:Netflix/consoleme.git
```

#### Start Redis and DynamoDB containers

A local set of Redis and DynamoDB (local) instances need to be set up. These are provided as Docker containers. In a separate terminal window, start the local redis and dynamodb instances:

```bash
docker-compose -f docker-compose-dependencies.yaml up
```

#### Get access to administrative credentials on your account

For an initial setup, we advise making an IAM user with sufficient privileges to allow ConsoleMe to sync your IAM roles,
S3 buckets, SQS queues, SNS topics, and AWS Config data. Sections below outline the required permissions. See
[this page](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) for configuring your user
credentials. Note: After you have ConsoleMe set up, you should no longer need IAM user credentials. Please set a
reminder to delete these when you're done with them.

#### Make a virtual environment and run the installation script

In repo root run `make install`. You may also want to install the default plugins if you have not developed internal plugins: `pip install -e default_plugins`

```bash
# Make a Python 3.8 Virtual Environment using your preferred method. Here's a standard way of doing it:
python3 -m venv env

# Activate virtualenv
. env/bin/activate

make install
# The `make install` step runs the following commands, and attempts to create local dynamo tables:
#
# pip install -r requirements.txt -r requirements-test.txt -e default_plugins -e .
# yarn
# node_modules/webpack/bin/webpack.js --progress
# python scripts/initialize_dynamodb_oss.py
# python scripts/initialize_redis_oss.py
```

> You will need to have AWS credentials for the installation to work (they need to be valid credentials for any
> account or user for the AWS SDK to communicate with the local DynamoDB container).

#### Run ConsoleMe with the default configuration

```bash
# Run ConsoleMe
python consoleme/__main__.py
```

> ConsoleMe requires Python 3.8+. If your virtualenv was installed under Python2.x
> this will blow up. You can usually fix this by uninstalling and reinstalling under python3.x by removing your existing
> virtualenv and creating a new one with Python 3: `python3 -m venv env`.
> When the `make install` command is running, it will install all the dependencies, and it will also run ConsoleMe
> Celery tasks to populate its Redis cache if necessary. This also updates the local DynamoDB instance, which persists
> data on disk. This command will need to be run anytime you want to update your local cache.

### Configure your browser

You can either use the `example_config/example_config_development.yaml` as your configuration to override the user you
are authenticated as for development, or you can Configure a header injector such as
[Requestly](https://www.requestly.in/) to inject user / group headers. By default, the header names are in your
configuration file. In our example configurations, they are specified in `example_config_base.yaml` under the
`auth.user_header_name` and `auth.groups_header_name` keys. The user header should be an email address, i.e.
`you@example.com`. The groups header should be a list of comma-separated groups that you are a member of, i.e.
`group1@example.com,group2@example.com,groupx@example.com, groupy`. Groups do not need to be an email address.

You can see which headers are being passed to ConsoleMe by visiting the [`/myheaders` endpoint](http://localhost:8081/myheaders)
in ConsoleMe.

> Make sure you have at least two groups in your list, otherwise every time you visit your local consoleme Role page it will auto-login to the console with your one role.

### Browse to ConsoleMe

You should now be able to access the ConsoleMe web UI at http://localhost:8081. Success! 🎉

### Role configuration

By now, you should have the ConsoleMe web UI running, though it probably can't do much at the moment. This is where
you'll need to configure ConsoleMe for your environment. The ConsoleMe service needs its own user/role (with an
InstanceProfile for EC2 deployment), and each of your accounts should have a role that ConsoleMe can assume into.

#### ConsoleMeInstanceProfile configuration

Firstly, the ConsoleMe service needs its own user or role. Note that ConsoleMe has a lot of permissions. You should
ensure that its privileges cannot be used outside of ConsoleMe, except by authorized administrators (Likely, you).

You can call this new role "ConsoleMeInstanceProfile". It will also need to assume whichever roles you want to allow it
to assume in your environment. Here is a full-fledged
policy you can use when deploying to production. For now, scoping down assume role rights for testing should be
sufficient. Create an inline policy for your role with the following permissions if you never want to have to
think about it again:

Replace `arn:aws:iam::1243456789012:role/consolemeInstanceProfile` in the Assume Role Trust Policy with your ConsoleMe
service role ARN.

```json
{
  "Statement": [
    {
      "Action": [
        "cloudtrail:*",
        "cloudwatch:*",
        "config:*",
        "dynamodb:batchgetitem",
        "dynamodb:batchwriteitem",
        "dynamodb:deleteitem",
        "dynamodb:describe*",
        "dynamodb:getitem",
        "dynamodb:getrecords",
        "dynamodb:getsharditerator",
        "dynamodb:putitem",
        "dynamodb:query",
        "dynamodb:scan",
        "dynamodb:updateitem",
        "sns:createplatformapplication",
        "sns:createplatformendpoint",
        "sns:deleteendpoint",
        "sns:deleteplatformapplication",
        "sns:getendpointattributes",
        "sns:getplatformapplicationattributes",
        "sns:listendpointsbyplatformapplication",
        "sns:publish",
        "sns:setendpointattributes",
        "sns:setplatformapplicationattributes",
        "sts:assumerole"
      ],
      "Effect": "Allow",
      "Resource": ["*"]
    },
    {
      "Action": ["ses:sendemail", "ses:sendrawemail"],
      "Condition": {
        "StringLike": {
          "ses:FromAddress": ["email_address_here@example.com"]
        }
      },
      "Effect": "Allow",
      "Resource": "arn:aws:ses:*:123456789:identity/your_identity.example.com"
    },
    {
      "Statement": [
        {
          "Action": [
            "autoscaling:Describe*",
            "cloudwatch:Get*",
            "cloudwatch:List*",
            "config:BatchGet*",
            "config:List*",
            "config:Select*",
            "ec2:DescribeSubnets",
            "ec2:describevpcendpoints",
            "ec2:DescribeVpcs",
            "iam:*",
            "s3:GetBucketPolicy",
            "s3:GetBucketTagging",
            "s3:ListAllMyBuckets",
            "s3:ListBucket",
            "s3:PutBucketPolicy",
            "s3:PutBucketTagging",
            "sns:GetTopicAttributes",
            "sns:ListTagsForResource",
            "sns:ListTopics",
            "sns:SetTopicAttributes",
            "sns:TagResource",
            "sns:UnTagResource",
            "sqs:GetQueueAttributes",
            "sqs:GetQueueUrl",
            "sqs:ListQueues",
            "sqs:ListQueueTags",
            "sqs:SetQueueAttributes",
            "sqs:TagQueue",
            "sqs:UntagQueue"
          ],
          "Effect": "Allow",
          "Resource": "*"
        }
      ],
      "Version": "2012-10-17"
    }
  ],
  "Version": "2012-10-17"
}
```

Configure the trust policy with the following settings (Yes, you'll want to allow ConsoleMe to assume itself):

```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      }
    },
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::1243456789012:role/consolemeInstanceProfile"
      }
    }
  ],
  "Version": "2012-10-17"
}
```

#### ConsoleMe role configuration

Each of your accounts needs a role that ConsoleMe can assume. It uses this role to cache information from the account.
ConsoleMe will cache IAM roles, S3 buckets, SNS topics, and SQS queues by default. If you have it configured, it will
also cache data from the AWS Config service for IAM policy/self-service typeahead and for the Policies table.

Note that these permissions are pretty hefty. Be sure to lock things down more here if appropriate for your environment,
and again, ensure that this role is protected and can only be altered/use by administrative users.

Replace `arn:aws:iam::1243456789012:role/consolemeInstanceProfile` in the Assume Role Trust Policy with your ConsoleMe
service role ARN.

```json
{
  "Statement": [
    {
      "Action": [
        "autoscaling:Describe*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "config:BatchGet*",
        "config:List*",
        "config:Select*",
        "ec2:DescribeSubnets",
        "ec2:describevpcendpoints",
        "ec2:DescribeVpcs",
        "iam:*",
        "s3:GetBucketPolicy",
        "s3:GetBucketTagging",
        "s3:ListAllMyBuckets",
        "s3:ListBucket",
        "s3:PutBucketPolicy",
        "s3:PutBucketTagging",
        "sns:GetTopicAttributes",
        "sns:ListTagsForResource",
        "sns:ListTopics",
        "sns:SetTopicAttributes",
        "sns:TagResource",
        "sns:UnTagResource",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ListQueues",
        "sqs:ListQueueTags",
        "sqs:SetQueueAttributes",
        "sqs:TagQueue",
        "sqs:UntagQueue"
      ],
      "Effect": "Allow",
      "Resource": ["*"],
      "Sid": "iam"
    }
  ],
  "Version": "2012-10-17"
}
```

Assume Role Policy Document:

```json
{
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::1243456789012:role/consolemeInstanceProfile"
      }
    }
  ],
  "Version": "2012-10-17"
}
```

### Service configuration

You should have the ConsoleMe web service up and running, and you should have some roles that ConsoleMe can use or
assume. Now comes the fun part: Configuring ConsoleMe.

At Netflix, we use our production ConsoleMe service to get credentials for ConsoleMe locally
(hence why ConsoleMeInstanceProfile needs to be able to assume itself). For a first-time setup, you may not have this
luxury. If you're using an IAM user, let it assume into the consolemeinstanceprofile service role that you created in
the previous step (If you take this route, we recommend removing those permissions as soon as you deploy consoleme and
can retrieve credentials from ConsoleMe in your production environment). You'll need to put the role's credentials in
environmental variables or your ~/.aws/credentials file locally for now so that ConsoleMe can find them. (ConsoleMe uses
boto3, which like all AWS SDKs, looks for credentials [in the following order](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/credentials.html#credentials-default).)

Once we have this up and running, we can rely on role tags to determine which users/groups are authorized to retrieve
credentials for a role. Alternative, ou can statically define a map in your configuration of what roles to display, and
specify which users/groups are authorized to access which roles in your environment.

#### Authorization based on role tags

The configuration below enables authorization by role tags. In the example below, if a role is tagged with:

```bash
consoleme-authorized=user1@example.com:group1
```

User user1@example.com and members of the group `group1` will be able to get credentials for the role, and will also
be able to access the AWS Console using the role's credentials on the ConsoleMe web interace.

Conversely, if a role had the `consoleme-authorized-cli-only` tag configured, users would be able to get credentials
for the role via the CLI, but they would not see the role in ConsoleMe's web interface.

```yaml
cloud_credential_authorization_mapping:
  role_tags:
    enabled: true
    authorized_groups_tags:
      - consoleme-authorized
    authorized_groups_cli_only_tags:
      - consoleme-owner-dl
      - consoleme-authorized-cli-only
```

#### Static authorization mapping

In your configuration, you'll want to specify an `account_ids_to_name` mapping of your AWS accounts. An example is
provided in [example_config/example_config_base.yaml]:

```yaml
account_ids_to_name:
  123456789012: default_account
  123456789013: prod
  123456789014: test
```

You'll also want to provide a mapping of which users/groups can access which roles. We use a dynamic configuration
in our production environment to specify this mapping. This can be updated on the fly and will allow users to see newly
authorized roles within a minute. Locally, we can either use Local DynamoDB for our dynamic configuration or just
override the dynamic_config keyspace in our configuration. Here is what you can add to your yaml configuration.
group_mapping maps a user's e-mail address, or a group e-mail address to a list of IAM roles.

```yaml
dynamic_config:
  group_mapping:
    groupa@example.com:
      roles:
        - arn:aws:iam::123456789012:role/roleA
        - arn:aws:iam::123456789012:role/roleB
    userb@example.com:
      roles:
        - arn:aws:iam::123456789012:role/roleA
```

Once you have this configured, restart ConsoleMe locally and force-refresh your JWT by visiting:
[http://localhost:8081?refresh_cache=true](http://localhost:8081?refresh_cache=true)

For development only, you can override your local user and groups:

```yaml
# A development configuration can specify a specific user to impersonate locally.
_development_user_override: consoleme_admin@example.com

# A development configuration can override your groups locally
_development_groups_override:
  - groupa@example.com
  - groupb@example.com
  - configeditors@example.com
  - consoleme_admins@example.com
```

## Development

### Docker development

ConsoleMe can be developed solely within a docker container. Using the following command, the container will automatically be built and run. Your AWS secrets from ~/.aws/credentials will be placed on volumes in the container.

```bash
docker-compose -f docker-compose.yaml -f docker-compose-dependencies.yaml up
```

### Local DynamoDB

Running `docker-compose -f docker-compose-dependencies.yaml up` in the root directory will enable local dynamodb and local redis. To install a web interface
to assist with managing local dynamodb, install dynamodb-admin with:

```bash
npm install dynamodb-admin -g

# You need to tell dynamodb-admin which port dynamodb-local is running on when running dynamodb-admin
DYNAMO_ENDPOINT=http://localhost:8005 dynamodb-admin
```

### Update Dependencies

To update the `pip` Python dependencies, run this command:

```bash
make up-reqs
```

> If you're using Python 3.8 and trying to run this command on Mac, you may need to run
> `PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig" make up-reqs` which forces pkgconfig to use
> brew's xmlsec instead of the MacOS xmlsec (Details: https://github.com/mehcode/python-xmlsec/issues/111)

### Releases and Versioning

ConsoleMe uses [setupmeta](https://github.com/zsimic/setupmeta) for versioning, utilizing the [`devcommit` strategy](https://github.com/zsimic/setupmeta/blob/master/docs/versioning.rst#devcommit). This project adheres to [SemVer standards](https://semver.org/#summary) for major, minor, and patch versions. `setupmeta` diverges from SemVer slightly for development versions.

When you're ready to release **patch** changes on `master`:

```bash
python setup.py version --bump minor --commit --push
```

When you're ready to release **minor** changes on `master`:

```bash
python setup.py version --bump minor --commit --push
```

When you're ready to release **major** changes on `master` (rare, reserved for breaking changes):

```bash
python setup.py version --bump major --commit --push
```

### Running async functions

To run an async python function syncronously in a shell for testing:

```python
import asyncio
asyncio.get_event_loop().run_until_complete(<function>)
```

### PyCharm Unit Testing

To run tests in PyCharm, the clearly superior Python development environment, you need to update your Debug
configuration to include the following environment variables to assist with debugging:

- `CONFIG_LOCATION=/location/to/your/test.yaml` (Required)
- `ASYNC_TEST_TIMEOUT=9999999` (Optional for debugging the RESTful code)

Run `make test` or `make testhtml` to run unit tests

> Recommended: Run with the `Additional Arguments` set to `-n 4` to add some concurrency to the unit test execution.

### SAML

1. Update ConsoleMe's configuration with your configuration parameters (This is under `get_user_by_saml_settings`). [Example](example_config/example_config_saml.yaml)
1. Put your Service Provider certificate and private key in the location you specified in your
   `get_user_by_saml_settings.saml_path` configuration value. Default: [example_config/saml_example/certs/](example_config/saml_example/certs/)
   as `sp.crt` and `sp.key`. (You can generate a certificate and private key with the following command:
   `openssl req -x509 -nodes -sha256 -days 3650 -newkey rsa:2048 -keyout sp.key -out sp.crt`)
1. Start ConsoleMe with your desired configuration, and test the flow:

```bash
CONFIG_LOCATION=example_config/example_config_saml.yaml python consoleme/__main__.py
```

Important configuration variables:

`get_user_by_saml_settings.idp_metadata_url`: The URL of the SAML Metadata that ConsoleMe can load SAML configuration from.
`get_user_by_saml_settings.saml_path`: Location of SAML settings used by the OneLoginSaml2 library - You'll need to configure the entity ID, IdP Binding urls, and ACS urls in this file

`get_user_by_saml_settings.jwt`: After the user has authenticated, ConsoleMe will give them a jwt valid for the time specified in this configuration, along with the jwt attribute names for the user's email and groups.

`get_user_by_saml_settings.attributes`: Specifies the attributes that we expect to see in the SAML response, including the user's username, groups, and e-mail address

### OpenID Connect & OAuth 2.0

1. Update ConsoleMe's configuration with your configuration parameters (This is under `get_user_by_oidc_settings`). [Example](example_config/example_config_oidc.yaml)
1. Update ConsoleMe's configuration with your client ID, client secret, and scopes. (This is under `oidc_secrets`). [Example](example_config/example_secrets.yaml)
1. Start ConsoleMe with your desired configuration, and test the flow:

```bash
CONFIG_LOCATION=example_config/example_config_oidc.yaml python consoleme/__main__.py
```

### Local development with Docker (PyCharm specific instructions) # TODO: Docs with screenshots

It is possible to use Docker `docker-compose-test.yaml` to run ConsoleMe and its dependencies locally
in Docker with the default plugin set. Configure a new Docker Python interpreter to run **main**.py with your
working directory set to `/apps/consoleme` (on the container). This flow was tested on Windows 10.

### Generating Models from Swagger Spec

When changes are made to the Swagger spec, models may need to be regenerated using [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator).

```bash
pip install datamodel-code-generator
datamodel-codegen --input swagger.yaml --output consoleme/models.py
```

## Generate an AMI to deploy ConsoleMe to EC2

To generate an AMI, retrieve sufficiently privileged credentials locally and run `make create_ami`.

## Override a Route

If you wish to override a handler for a web route in routes.py, you can specify an internal route for it which will take precedence. For example, if you wanted to override the index page, you would modify your internal route plugin with the new route. The included [default_plugins](default_plugins/consoleme_default_plugins/plugins/internal_routes/handlers/internal_demo_route.py) has an example internal route.
