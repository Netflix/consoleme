# ConsoleMe

ConsoleMe is a multi-account AWS Swiss Army knife, making AWS usage easier for end-users and cloud administrators alike.

ConsoleMe achieves this through:

- consolidating the management of multiple accounts into a single web interface.
- allowing end-users and administrators to get credentials and console access to your onboarded accounts based on their authorization level.
- providing mechanisms for end-users and administrators to request and manage permissions for IAM roles, S3 buckets, SQS queues, SNS topics, and more.
- surfacing a powerful self-service wizard which empowers users to express their high level intent and request the permissions right for them

More details [here](https://hawkins.gitbook.io/consoleme/)

## Introduction

This chart creates two Pods in a Deployment, one running a ConsoleMe instance and other one running the Celery tasks.
The deployment of a local DynamoDB is available for testing purposes.
Elasticache is recommended for production environments, but you can use the Redis deployment using the Redis Helm chart (Helm dependency).

## Dependencies

Redis Helm Chart when the option redis.deployLocal = true

## Prerequisites

- Helm 3+
- Kubernetes 1.16+

## Required Configuration

Please check this [page](https://hawkins.gitbook.io/consoleme/prerequisites/required-iam-permissions) to create the necessary roles in the right accounts to make it accessible by ConsoleMe.

## Customization

The following table lists the main configurable parameters of the ConsoleMe chart and their default values.

| Parameter                                                  | Description                                                                                                                                                                                   | Default                                                                                                                                 |
| :--------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- |
| `image.repository`                                         | Container image used by ConsoleMe and Celery instances                                                                                                                                        | `consoleme/consoleme`                                                                                                                   |
| `image.pullPolicy`                                         | Policy to pull the container images                                                                                                                                                           | `IfNotPresent`                                                                                                                          |
| `image.tag`                                                | Image tag                                                                                                                                                                                     | `latest`                                                                                                                                |
| `sentry.dsn`                                               | Sentry DSN to send exceptions                                                                                                                                                                 | `N/A`                                                                                                                                   |
| `tornado`                                                  | These are the tornado settings. Set `debug` to false in production.                                                                                                                           | `{}`                                                                                                                                    |
| `redis.deployLocal`                                        | Flag to activate the Redis deployment via the dependency Redis Helm chart                                                                                                                     | `false`                                                                                                                                 |
| `redis.broker_url`                                         | Redis broker URL in the format redis://HOST:PORT/DATABASE. For local Redis use redis://consoleme-redis-master:6379/1                                                                          | `N/A`                                                                                                                                   |
| `redis.region`                                             | Redis region location                                                                                                                                                                         | `N/A`                                                                                                                                   |
| `redis.host`                                               | Redis host address                                                                                                                                                                            | `N/A`                                                                                                                                   |
| `dynamodb.deployLocal`                                     | Flag to activate the DynamoDB deployment. For local DynamoDB use http://consoleme-dynamodb:8005                                                                                               | `false`                                                                                                                                 |
| `dynamodb.url`                                             | DynamoDB URL to be used with local deployment, must be empty if using AWS DynamoDB service                                                                                                    | `""`                                                                                                                                    |
| `authentication.type`                                      | Web App Authentication and Authorization, supported values: header, alb, oidc, saml. More details [here](https://hawkins.gitbook.io/consoleme/configuration/authentication-and-authorization) | `header`                                                                                                                                |
| `authentication.header_config`                             | To be used **only** if authentication.type is **header**. Please check the file example_config/example_config_header_auth.yaml to find right the parameters                                   | `{}`                                                                                                                                    |
| `authentication.alb_config`                                | To be used **only** if authentication.type is **alb**. Please check the file example_config/example_config_alb_auth.yaml to find right the parameters                                         | `{}`                                                                                                                                    |
| `authentication.saml_config`                               | To be used **only** if authentication.type is **saml**. Please check the file example_config/example_config_saml.yaml to find right the parameters                                            | `{}`                                                                                                                                    |
| `authentication.oidc_config`                               | To be used **only** if authentication.type is **oidc**. Please check the file example_config/example_config_oidc.yaml to find right the parameters                                            | `{}`                                                                                                                                    |
| `groups`                                                   | Group definition, available groups: can_admin, can_admin_policies, development_notification_emails, can_edit_config, can_edit_policies, can_create_roles, can_delete_roles                    | `{}`                                                                                                                                    |
| `groups.fallback_policy_request_reviewers`                 | Default email address receiving policy reviews                                                                                                                                                | `[]`                                                                                                                                    |
| `config.load_from_dynamo`                                  | Load configuration from DynamoDB                                                                                                                                                              | `false`                                                                                                                                 |
| `cloud_credential_authorization_mapping`                   | Tags used to define the IAM roles which user/group are authorized to access. Please check the file example_config/example_config_base.yaml to find the right parameters                       | `{}`                                                                                                                                    |
| `account_ids_to_name`                                      | Dictionary of AWS accounts to be used by ConsoleMe                                                                                                                                            | `{}`                                                                                                                                    |
| `aws.issuer`                                               | Your company's name                                                                                                                                                                           | `YourCompany`                                                                                                                           |
| `aws.account_number`                                       | Your AWS main account number                                                                                                                                                                  | `""`                                                                                                                                    |
| `aws.region`                                               | The region used by the main account                                                                                                                                                           | `us-east-1`                                                                                                                             |
| `challenge_url`                                            | Challenge URL authentication is used to authenticate users from CLI clients (like Weep).                                                                                                      | `{}`                                                                                                                                    |
| `consoleme.environment`                                    | Instance environment                                                                                                                                                                          | `prod`                                                                                                                                  |
| `consoleme.development`                                    | Flag to activate development mode                                                                                                                                                             | `true`                                                                                                                                  |
| `consoleme.url`                                            | ConsoleMe URL                                                                                                                                                                                 | `http://localhost:8081`                                                                                                                 |
| `consoleme.application_admin`                              | Admin username                                                                                                                                                                                | `consoleme_admins@example.com`                                                                                                          |
| `consoleme.jwt_secret`                                     | JWT secret                                                                                                                                                                                    | `secret`                                                                                                                                |
| `consoleme.web`                                            | Configuration used in ConsoleMe instance deployment                                                                                                                                           | `{}`                                                                                                                                    |
| `consoleme.celery`                                         | Configuration used in Celery Scheduler instance deployment                                                                                                                                              | `{}`                                                                                                                                    |
| `consoleme.celery_worker`                                  | Configuration used in Celery Worker instance deployment                                                                                                                                              | `{}`                                                                                                                                    |
| `policies.role_name`                                       | Role to be assumed by ConsoleMe                                                                                                                                                               | `{}`                                                                                                                                    |
| `policies.supported_resource_types_for_policy_application` | Resource types supported for policy application                                                                                                                                               | `["s3", "sqs", "sns"]`                                                                                                                  |
| `user_role_creator.default_trust_policy`                   | Trust policy to be added to new roles                                                                                                                                                         | `{"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": {"Service": "ec2.amazonaws.com"},"Action": "sts:AssumeRole"}]}` |
| `ses`                                                      | SES configuration is necessary for ConsoleMe to send e-mails to your users. ConsoleMe sends e-mails to notify administrators and requesters about policy requests applicable to them          | `{}`                                                                                                                                    |
| `ingress`                                                  | Ingress configuration, default is disabled                                                                                                                                                    | `{}`                                                                                                                                    |
| `autoscaling`                                              | Activate HPA for the deployments. Resources must be set in ConsoleMe to use HPA. Default is disabled                                                                                          | `{}`                                                                                                                                    |
| `self_service_iam`                                         | Default templates to be used by the Self-Service                                                                                                                                              | Reference the default values provided in consoleme/lib/defaults.py as SELF_SERVICE_IAM_DEFAULTS                                         |
| `permission_templates`                                     | Default templates to be used by the Policy Editor                                                                                                                                             | Reference the default values provided in consoleme/lib/defaults.py as PERMISSION_TEMPLATE_DEFAULTS                                      |

## Deploying

### Local Chart Deployments

If you have access to this helm chart locally, here are some useful deployment commands.

To perform a dry-run execution of the deployment (helm version 3+):

```bash
helm install my-consoleme -f values.yaml . --dry-run --debug
```

To preview the template generated:

```bash
helm template . --dry-run --debug -f values.yaml
```

To install the helm chart:

```bash
helm install my-consoleme -f values.yaml my-consoleme .
```

### Remote Chart Deployments

If you want to reference this helm chart remotely, here are some useful deployment commands.

First, add [the `helm-git` plugin](https://github.com/aslafy-z/helm-git):

```bash
helm plugin install https://github.com/aslafy-z/helm-git --version 0.10.0
```

Now, add consoleme chart to your local helm repos:

```bash
helm repo add consoleme "git+ssh://git@github.com/Netflix/consoleme@helm?ref=master"
```

Now, deploy consoleme:

```bash
helm install my-consoleme consoleme/consoleme
```
