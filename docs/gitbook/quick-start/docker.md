---
description: >-
  Provides instructions for getting ConsoleMe up and running locally through
  Docker.
---

# Docker

## Docker

Docker-Compose is the quickest way to get ConsoleMe up and running locally for **testing** purposes. For **development**, we highly recommend setting up ConsoleMe locally with the instructions below this Quick Start. The Dockerfile is a great point of reference for the installation process. If you are going to deploy ConsoleMe in a production environment, we recommend deploying it to an isolated, locked-down AWS account.

Firstly, clone ConsoleMe locally in a directory of your choosing:

```text
git clone git@github.com:Netflix/consoleme.git ; cd consoleme
```

**BEFORE RUNNING THE COMMAND BELOW**: We highly recommend that you put valid AWS credentials for your account in your ~/.aws/credentials file. The role you use should have the permissions outlined under `ConsoleMeInstanceProfile configuration` below. These credentials will be shared with the container, and when you run the second command to populate your Redis cache \(`make redis`\) command using docker exec, it will attempt to populate your redis cache with live resources from your account. This will only work if you have valid AWS credentials.

To start up ConsoleMe in docker, run the following command:

```text
# Ensure that you have valid AWS Credentials in your ~/.aws/credentials file under your `default` profile
# before running this command. This command will cache AWS resources for the
# account.
docker-compose -f docker-compose.yaml -f docker-compose-dependencies.yaml up -d
```

After this is done, visit `http://localhost:3000`. You may notice the page is rather empty. One of the containers we started should be initializing your redis cache with your AWS account resources, so you may need to give it a moment. To follow along with resource caching, run the following docker command:

```text
docker container logs -f consoleme-celery
```

By default, you're running ConsoleMe as an administrator, using the local [Docker development configuration](example_config/example_config_docker_development.yaml)**.** This configuration does not implement authn/authz and is not intended to be used in a production environment.

If successful, ConsoleMe should have been able to cache all of your resources. But you'll notice that you're unable to access any IAM roles with the default configuration. This is because we cannot generate an authorization mapping 

