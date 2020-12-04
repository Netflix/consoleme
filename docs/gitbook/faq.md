# FAQ

## How do I override one of ConsoleMe's web routes, or add new routes just for my internal implementation of ConsoleMe?

You can add new routes or override existing routes in your implementation of ConsoleMe through the use of an internal plugin. ConsoleMe provides a set of default plugins that serve as an example of how you should implement your internal plugins. 

Included in the default\_plugins set is a list of [internal routes](https://github.com/Netflix/consoleme/blob/master/default_plugins/consoleme_default_plugins/plugins/internal_routes/internal_routes.py) and an example [web handler](https://github.com/Netflix/consoleme/blob/master/default_plugins/consoleme_default_plugins/plugins/internal_routes/handlers/internal_demo_route.py#L9). The routes defined here will take precedence over ConsoleMe's [default routes](https://github.com/Netflix/consoleme/blob/master/consoleme/routes.py#L91). 

## How can I generate an AMI for ConsoleMe so I can deploy it to EC2?

We provide an example flow to generating an AMI based on ConsoleMe's default configuration. This should serve as a reference for you to create your own AMI. Here are the general steps you'd need to follow to get this running today. We are looking for contributions to make this process smoother:

1. Install Packer with the guidance [here](https://learn.hashicorp.com/tutorials/packer/getting-started-install).
2. Retrieve AWS credentials locally \(Place them in your ~/.aws/credentials file under the default profile, or set them as environment variables\)
3. Place your custom configuration in a file called `consoleme.yaml` in your ConsoleMe directory
4. Run `make create_ami`from your ConsoleMe directory. This process will compress the current directory and create an Ubuntu AMI for ConsoleMe

## How do I generate models from the Swagger specification?

We use [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) to generate Pydantic models for ConsoleMe.

If you make changes to [ConsoleMe's Swagger specification](https://github.com/Netflix/consoleme/blob/master/swagger.yaml), you'll need to re-generate the [Pydantic Models file ](https://github.com/Netflix/consoleme/blob/master/consoleme/models.py)with the following command:

```text
datamodel-codegen --input swagger.yaml --output consoleme/models.py
```



