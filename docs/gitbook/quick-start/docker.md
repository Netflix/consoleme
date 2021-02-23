---
description: >-
  Provides instructions for getting ConsoleMe up and running locally through
  Docker.
---

# Docker

## Docker

Docker-Compose is the quickest way to get ConsoleMe up and running locally for **testing** purposes. For **development**, we highly recommend setting up ConsoleMe locally with the instructions below this Quick Start. The Dockerfile is a great point of reference for the installation process. If you are going to deploy ConsoleMe in a production environment, we recommend deploying it to an isolated, locked-down AWS account.

Firstly, install [**git**](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), [**docker**](https://docs.docker.com/get-docker/), and [**docker-compose**](https://docs.docker.com/compose/install/) ****on your system, consider following [Docker's post-installation steps for Linux](https://docs.docker.com/engine/install/linux-postinstall/), then clone ConsoleMe locally in a directory of your choosing via HTTP or SSH:

```text
git clone https://github.com/Netflix/consoleme.git ; cd consoleme

# OR # 

git clone git@github.com:Netflix/consoleme.git ; cd consoleme
```

{% hint style="info" %}
**BEFORE RUNNING THE COMMAND BELOW**: We highly recommend that you put valid AWS credentials for your account in your `~/.aws/credentials` file under the `[default]` profile \([Instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-where)\). The role you use should have the permissions outlined under [Central Account IAM Permissions](../prerequisites/required-iam-permissions/central-account-consolemeinstanceprofile.md). These credentials will be shared with the container, and when you run the second command to populate your Redis cache \(`make redis`\) command using docker exec, the command will attempt to populate your redis cache with live resources from your account. This will only work if you have valid AWS credentials.
{% endhint %}

To start up ConsoleMe in docker, run the following command:

```text

docker-compose -f docker-compose-dockerhub.yaml -f docker-compose-dependencies.yaml up -d
# If you wish to build ConsoleMe instead of using a pre-build image, run this command:
# docker-compose -f docker-compose.yaml -f docker-compose-dependencies.yaml up -d
```

At this point you should the below command and verify you have 4 ConsoleMe related containers running.

* consoleme-celery
* consoleme
* dynamodb-local
* redis:alpine

```text
docker ps
```

Your output should resemble the following screenshot:

![](../.gitbook/assets/image%20%288%29.png)

If you do not have 4 containers running, run the docker compose command again to ensure they are started.

After this is done, wait a bit for the containers to fully start. Run `docker logs <container_id>` to check progress and observe errors from the running ConsoleMe containers.

  `http://localhost:3000`. You may notice the page is rather empty. One of the containers we started should be initializing your redis cache with your AWS account resources, so you may need to give it a moment. To follow along with resource caching, run the following docker command:

```text
docker container logs -f consoleme_consoleme-celery_1
```

By default, you're running ConsoleMe as an administrator, using the local [Docker development configuration](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_docker_development.yaml)**.** This configuration does not implement authn/authz and is not intended to be used in a production environment.

If successful, ConsoleMe should have been able to cache all of your resources. But you'll notice that you're unable to access any IAM roles with the default configuration. You'll need to follow the guidance under [Role Credential Authorization](../configuration/role-credential-authorization/) to grant access to role credentials to your users and/or the groups they are members of.

## Create your Configuration

At this point, you'll want to configure ConsoleMe to suit your needs. Read up on [ConsoleMe’s yaml configuration.](../configuration/) ConsoleMe can be configured to [authenticate your users via SAML, OIDC, header authentication, or it can bypass authentication altogether](../configuration/authentication-and-authorization/).  

To get started, copy [this configuration](https://gist.github.com/castrapel/888cd106d12523a5445bf6f3cf9c810b). Read through the configuration and change the values to suit your environment. 

