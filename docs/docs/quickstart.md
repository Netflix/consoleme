---
id: QuickStart
title: Quick Start
---

ConsoleMe provides a unified AWS login experience across hundreds of accounts. Currently, we support OAuth,
SAML, Google Groups, and LDAP for authentication. We encourage open source contributions for others.
If you have a customized internal authentication system, ConsoleMe is pluggable and customizable. We encourage you to
write internal plugins for your custom business logic.

## Local Quick Start with Header Authentication (Docker)
1. [Install Docker and Docker-Compose](https://github.com/Yelp/docker-compose/blob/master/docs/install.md)
1. Run `docker-compose up`
1. Visit [http://127.0.0.1:8081](http://127.0.0.1:8081). If everything is working as expected, you should see a message
stating "No user detected. Check configuration.". This indicates that the web server is listening to requests.
1. Inject a header to specify your e-mail address and groups. ([Requestly](https://www.requestly.in/) works well).

    * The headers needed are specified under the `auth.user_header_name` and `auth.groups_header_name` keys in
     docker/example_config_header_auth.yaml. By default, they are `user_header` and `groups_header` respectively.
     You are encouraged to make own configuration file.

    * If you set your user to `user@example.com` and your groups to
    `groupa@example.com,groupb@example.com,configeditors@example.com,admin@example.com`, you should see a couple of
    example roles in the UI.

    * If you would like to use header authentication in a production environment, You *must* configure a web server or
    load balancer to perform authentication on ConsoleMe's behalf. The server in front of ConsoleMe should drop the header
    you use for authentication from incoming requests (To prevent users from forging their identity), authenticate the user,
    then set the header for ConsoleMe to consume.
1. That's it! Check out the `Configuration Guide` for customizing ConsoleMe # TODO: Create and link to configuration guide


## Local DynamoDB
Running `docker-compose up` in the root directory will enable local dynamodb and local redis. To install a web interface
to assist with managing local dynamodb, install dynamodb-admin with:

`npm install dynamodb-admin -g`
You need to tell dynamodb-admin which port dynamodb-local is running on when running dynamodb-admin:

`DYNAMO_ENDPOINT=http://localhost:8005 dynamodb-admin`

## Testing
Run your tests with the following environment variables:
- `CONFIG_LOCATION=/location/to/your/test.yaml` (Required)
- `ASYNC_TEST_TIMEOUT=999` (Optional for debugging the RESTful code)

Run `make test` or `make testhtml` to run unit tests
