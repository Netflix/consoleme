# Welcome to ConsoleMe CDK Deployment

## Motivation

ConsoleMe is a web service that makes AWS IAM permissions and credential management easier for end-users and cloud administrators.

The CDK deployment was created to help more people deploy ConsoleMe easily, authenticating with corporate
authentication tools and scaling without managing servers.

## Architecture

The main idea is to use serverless services in order to remove the need to manage servers.

![ConsoleMe on ECS Architecture](architecture.png "ConsoleMe on ECS Architecture")

## Usage

### Pre-requisites

- Domain name managed with a public hosted zone on AWS Route 53.
  Please collect this information and fill the `config.yaml` file with the hosted zone name and hosted zone id from Route 53.

  ```
  $ cp config.example.yaml config.yaml
  ```

In the config.yaml file, set a strong random password for the `admin_temp_password` key, and a different strong random
password for the `jwt_secret` key. You can use the following command to generate a strong random password:
`openssl rand -base64 16`.

- MacOS / Linux computer with Docker: https://docs.docker.com/get-docker/
- NodeJS 12 or later AWS CDK command line interface installed on your computer.
  You can easily install AWS CDK command line interface globally using `npm`:

  ```
  $ npm install -g aws-cdk
  ```

- AWS CDK assume role credential plugin. we're using this plugin in order to ease the deployment on a multi-account environment.
  You can easily install AWS CDK assume role credential plugin globally using `npm`:

  ```
  $ npm install -g cdk-assume-role-credential-plugin
  ```

- Python 3.6 and up with Pipenv dependencies & virtual environment management framework.
  You can easily install Pipenv command line interface it using `pip`:

  ```
  $ pip install --upgrade pipenv
  ```

- Use Pipenv to create and activate your virutal environment:
  To initiate the virtualenv on MacOS and Linux and install the required dependencies:

  ```
  $ pipenv install --dev
  ```

  After the init process completes, and the virtualenv is created, you can use the following
  step to activate your virtualenv.

  ```
  $ pipenv shell
  ```

- Bootstrap the CDK environment using the `modern` bootstrap template.
  This is required for each AWS account in order to enable the `trust` functionality
  which is required by the `cdk-assume-role-credential-plugin`.

  Main account bootstrapping:

  ```
  $ cdk bootstrap --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess --plugin cdk-assume-role-credential-plugin --context bootstrap=true
  ```

  Spoke accounts bootstrapping, trusting the main account bootstrapping:

  ```
  $ cdk bootstrap --trust $MAIN_AWS_ACCOUNT_ID --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess --plugin cdk-assume-role-credential-plugin --context bootstrap=true
  ```

### Preparing the CDK Environment

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and run `pipenv --lock && pipenv sync`
command.

### Deployment

You can now deploy all the CDK applications in all supported accounts:

Deploy trust role to spoke accounts:

```
$ cdk deploy ConsoleMeSpoke
```

Deploy ConsoleMe to main account:

```
$ cdk deploy ConsoleMeECS
```

Don't forget to approve the template and security resources before the deployment.
Deployment time for the main account should be less than 20 minutes.
You can control scaling of the ECS tasks amount on the `config.yaml` configuration file. The default is minimum of 2 tasks and maximum of 10 tasks.

### Docker

In order for the service to run, the ECS service containers will pull the compatible container image and provision containers according to the desired capacity.
For your convenience, by default we use the official `consoleme` docker image. However, you can configure the CDK deployment to build the current branch of `consoleme` and package it as a docker image hosted on ECR by modifying the `use_public_docker_image` parameter.
Also, the `aws-lambda-python` CDK construct is using docker to package the lambda function with all it's dependencies as a lambda layer.

### ConsoleMe Admin User

The CDK stack will provision the ConsoleMe administrator user. The user name supplied with this template is `consoleme_admin`.
You can set the user temporary password in the `config.yaml` file, login and update it afterwards (Cognito will ask you to do that).

## Security

- You should configure the admin user temporary password on the `config.yaml` file.
- You should set a new JWT secret for authentication purposes on the `config.yaml` file.
- During the deployment, a configuration file with all the relevant secrets is created and stored on an S3 bucket.
- Authentication to the ConsoleMe is done by AWS Cognito user pool.
- ECS containers are running in non-privileged mode, according to the docker best practices.
- During the deployment time, the cdk stack will try to determine your public ip address automatically using `checkip.amazonaws.com`.
  Then, it would add only this ip address to the ingress rules of the security group of the public load balancer.
- TLS termination are being done on the application load balancer using A SSL certificate generated on the deployment time by CDK, with DNS record validation on the configured hosted zone.
- Permanent resources, such as CMK, and Cognito User Pool are defined to be destroyed when the stack is deleted.
- Log groups retention are set to one week.

## Issues / Todo

- Allow adjusting compute sizes via configuration, such as Redis node size and containers CPU and RAM allocation.
- Elasticache authentication, rather than relying only on security groups for increased security.
- Separate task definitions for celery and ConsoleMe applications.
- Secret manager integration, instead of storing the secrets in clear text on the configuration file.