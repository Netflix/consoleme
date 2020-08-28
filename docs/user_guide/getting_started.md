## Feature List

- Promotes security hygiene through the use of IAM roles

IAM roles are more secure than IAM users because they do not
provide a method to get long-term credentials that might accidentally be leaked or committed to code. ConsoleMe assumes
roles in your environment and provides temporary one-hour credentials to authorized users.

We've included some quick-start docker-compose files that showcase some of the authentication methods supported
in ConsoleMe. You can also run ConsoleMe on Mac or Docker without Linux.

# Docker-Compose Instructions

You must install [Docker and Docker-Compose](https://github.com/Yelp/docker-compose/blob/master/docs/install.md) before
following the steps outlined in this section.

Before continuing, clone the ConsoleMe repo: `git clone https://github.com/Netflix/consoleme.git`

## SAML Demo

1. Run `docker-compose -f docker-compose-saml.yaml -f docker-compose-dependencies.yaml up` from the root directory of the `consoleme` repo.
1. Visit [Simplesaml metadata url](http://localhost:8080/simplesaml/saml2/idp/metadata.php?output=xml) and copy the
   x509 certificate for the IDP (The first `ds:X509Certificate` value), and replace the x509cert value specified in
   `docker/saml_example/settings.json`.
1. Visit [http://localhost:8081](http://localhost:8081)
1. Log in with username: `consoleme_user` and password `consoleme_user`.
1. You are redirected to ConsoleMe as an authenticated user.

To learn how to configure your own SAML provider, visit [SAML Configuration](saml.md).
Do not use the sample configurations provided here in a production environment, as they are insecure.

## OpenID Connect/OAuth 2.0 Demo

1. Run `docker-compose -f docker-compose-oidc.yaml -f docker-compose-dependencies.yaml up` from the root directory of the `consoleme` repo.
1. Visit [http://localhost:8081](http://localhost:8081)
1. Log in with username: `consoleme_user@example.com` and password `consoleme_user`.
1. You are redirected to ConsoleMe as an authenticated user.

To learn how to configure your own OIDC provider, visit [OpenID Connect/OAuth 2.0 Configuration](oidc.md).
Do not use the sample configurations provided here in a production environment, as they are insecure.

## Header Authentication Demo

If you run in an environment where authentication is handled for you, and you can use your provider to set headers
for downstream application, this is probably the flow that you want. ConsoleMe can be configured to parse the user's
e-mail address and/or groups from the received headers.

A word of caution: Ensure that you are properly dropping trusted headers before authentication. You do not want external
users to forge these headers.

## UserName and Password authentication

To make it easy to get started with ConsoleMe, we will add support for standalone authentication within ConsoleMe.
ConsoleMe will securely store user credentials with a salted hash. This is TBD.

## Local Quick Start with Header Authentication (Docker)

1. [Install Docker and Docker-Compose](https://github.com/Yelp/docker-compose/blob/master/docs/install.md)
1. Run `docker-compose up`
1. Visit [http://localhost:8081](http://localhost:8081). If everything is working as expected, you should see a message
   stating "No user detected. Check configuration.". This means that the web server is listening to requests.
1. Inject a header to specify your e-mail address and groups. ([Requestly](https://www.requestly.in/) works well).

   - The headers needed are specified under the `auth.user_header_name` and `auth.groups_header_name` keys in
     docker/example_config_header_auth.yaml. By default, they are `user_header` and `groups_header` respectively.
     You are encouraged to make own configuration file.

   - If you set your user to `user@example.com` and your groups to
     `groupa@example.com,groupb@example.com,configeditors@example.com,admin@example.com`, you should see a couple of
     example roles in the UI.

   - If you would like to use header authentication in a production environment, You _must_ configure a web server or
     load balancer to perform authentication on ConsoleMe's behalf. The server in front of ConsoleMe should drop the header
     you use for authentication from incoming requests (To prevent users from forging their identity), authenticate the user,
     then set the header for ConsoleMe to consume.

1. That's it! Check out the `Configuration Guide` for customizing ConsoleMe # TODO: Create and link to configuration guide

## Local Quick Start with SAML Authentication (Docker / KeyCloak)

TBD

## Local Quick Start with OAuth2/OIDC Authentication (Docker / KeyCloak)

TBD

## Deploy to AWS with ALB Authentication

TBD

## Configuration Guide

TBD

## Plugin Guide

ConsoleMe uses entry points to load various internal plugins for your internal-only business logic. We have included some
default plugins for reference, but as you start using more features in ConsoleMe, you'll probably find the default
plugins insufficient for your needs. We suggest that you copy the contents of the `default_plugins` folder into a
separate (private) repository and customize the included functions with logic custom to your organization. For example,
how should ConsoleMe determine the groups that your users are members of? How should ConsoleMe map these groups to
IAM roles? What type of session policy should ConsoleMe pass when logging a user in to a role? How should ConsoleMe figure
out where its configuration file is located?
The first entry poing

that you you'll probably want to copy this as a reference point

the `CONSOLEME_CONFIG_ENTRYPOINT` to determine the entry point for your internal configuration plugin.
This plugin will be consulted to determine which configuration file to use,

## Building ConsoleMe Locally

# OS X

1. Setup prerequisites

   1. Set up Python 3.7.2+ (`brew install python@3.7`)
   1. Install Xcode and ensure the command-line tools are installed (`xcode-select --install`)
   1. `brew install pkgconfig`
   1. `brew install libxmlsec1`
   1. [Install Docker and Docker-Compose](https://github.com/Yelp/docker-compose/blob/master/docs/install.md)

1. Clone the ConsoleMe repo: `git clone git@github.com:Netflix/consoleme.git`

1. A local set of Redis and DynamoDB (local) instances need to be set up. This is provided as a Docker container.
   In a separate terminal window, start the local Redis and Dynamodb instances: `docker-compose up`.

1. Create the virtualenv and activate it using your preferred method.
   Here's the standard way: `python3.7 -m venv env && source env/bin/activate`

1. You will need to have AWS credentials for the installation to work (they need to be valid credentials for any
   account or user for the AWS SDK to communicate with the local DynamoDB container). Configure these in your
   ~/.aws/credentials file or as environment variables. [Instructions](https://docs.aws.amazon.com/cli/latest/topic/config-vars.html#credentials)

1. Install the default_plugins package within ConsoleMe if you
   have not developed custom internal plugins: `pip install -e default_plugins`

1. In repo root run `make install`.

1. Run ConsoleMe with the default configuration:
   `CONSOLEME_CONFIG_ENTRYPOINT=default_config CONFIG_LOCATION=docker/example_config_header_auth.yaml python consoleme/__main__.py`
   _ Note: ConsoleMe requires Python 3.6+. We recommend running on 3.7. If your virtualenv was installed under Python2.x
   this will blow up. You can usually fix this by uninstalling and reinstalling under python3.x by removing your existing
   virtualenv and creating a new one with Python 3: `python3.7 -m venv env`.
   _ When the `make install` command is running, it will install all the dependencies, and it will also run ConsoleMe
   Celery tasks to populate its Redis cache if necessary. This also updates the local DynamoDB instance, which persists
   data on disk. This command will need to be run anytime you want to update your local cache.

1. Configure your browser header injector ([Requestly](https://www.requestly.in/) is recommended) to inject
   user / group headers. Your group headers should contain a comma-separated list of google or AD groups.
   You can see which headers are being passed to ConsoleMe by visiting the `/myheaders` endpoint in ConsoleMe. \* Note: Make sure you have at least two groups in your list, otherwise every time you visit your local Consoleme
   Role page it will auto-login to the console with your one role.

## Definitions

**ARN**: An Amazon Resource Name is a unique identifier to an Amazon Resource. Most, if not all AWS resources are provided a unique ARN that can be used in an IAM role policy to grant or restrict access to the resource. Each S3 bucket, SQS queue, SNS topic, RDS database, KMS key, IAM role, and more have unique ARNs. ARNs are also used in libraries to take an action on a resource.

**EC2 Instance Metadata Service**: A service that runs locally on EC2 instances, accessible through a link-local IP address. All AWS SDKs will automatically try to fetch details about the instance, including role credentials, from the EC2 Instance Metadata service if it is accessible. For more details, check out “Instance Metadata”. For more details about the order in which AWS SDKs will try to find credentials, take a look at “Working with AWS Credentials”.

**IAM**: AWS Identity and Access Management (IAM) allows us to manage a role’s access to AWS services and resources with a fine-grained set of permissions.

**IAM Instance Profile**: An instance profile is a logical unit that maps to an IAM role. As far as most users are concerned, IAM instance profiles and roles can be thought of as the same construct. For more details, see “Managing Instance Profiles”.

**IAM Role**: An IAM role is an identity in an AWS account with a set of permissions that define what actions are allowed and denied by an entity in AWS console. A role in IAM can be accessed by any entity (an individual or AWS service). For more details, check out “Roles Terms and Concepts”.

## To run an async python function syncronously in a shell for testing

import asyncio
asyncio.get_event_loop().run_until_complete(<function>)

## Docker development

If you want to develop solely within a docker container, run "docker-compose up". The container will be built and run.
Your AWS secrets from ~/.aws/credentials will be placed on volumes in the container.

## Local DynamoDB

Running `docker-compose up` in the root directory will enable local dynamodb and local redis. To install a web interface
to assist with managing local dynamodb, install dynamodb-admin with:

`npm install dynamodb-admin -g`
You need to tell dynamodb-admin which port dynamodb-local is running on when running dynamodb-admin:

`DYNAMO_ENDPOINT=http://localhost:8005 dynamodb-admin`

## Update Dependencies

To update the `pip` Python dependencies, run this command:

```
make up-reqs
```

If you're using Python 3.8 and trying to run this command on Mac, you will run into trouble. You may need to run
`PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig" make up-reqs` which forces pkgconfig to use
brew's xmlsec instead of the MacOS xmlsec (Details: https://github.com/mehcode/python-xmlsec/issues/111)

## PyCharm Unit Testing

To run tests in PyCharm, the clearly superior Python development environment, you need to update your Debug
configuration to include the following environment variables to assist with debugging:

- `CONFIG_LOCATION=/location/to/your/test.yaml` (Required)
- `ASYNC_TEST_TIMEOUT=9999999` (Optional for debugging the RESTful code)

Run `make test` or `make testhtml` to run unit tests

Recommended: Run with the `Additional Arguments` set to `-n 4` to add some concurrency to the unit test execution.
