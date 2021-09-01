# Deployment Strategies

Each organization is different in how they would wish to deploy ConsoleMe, and which specific operating system or base image they would want to deploy ConsoleMe on. We don't currently support or recommend any specific deployment flows. But we have a few resources that might help you get started. Help is definitely wanted in this area, so please contribute if you have guidance in this area.

## Create an Amazon AMI to deploy manually in EC2

ConsoleMe includes an example Packer configuration to assist with creating an image. You'll want to craft a custom configuration for ConsoleMe before creating an image, or be prepared to SSH into the instance you create to debug. Ensure that you have [Packer installed](https://learn.hashicorp.com/tutorials/packer/getting-started-install), and valid AWS credentials configured for the account you want the AMI deployed to.

To create an image with Packer, run the following command in the ConsoleMe repository:

`make create_ami`

## Deploy with Terraform

ConsoleMe has [example Terraform files ](https://github.com/Netflix/consoleme/tree/master/terraform) that can assist you with deploying ConsoleMe in a central account, and creating the roles that ConsoleMe needs in your spoke accounts. The central account configuration does not currently handle ACM \(for TLS certificates\), Route53, or load balancing.

## Deploy to ECS with a Docker Image

ConsoleMe has an example [docker-compose deployment file ](https://github.com/Netflix/consoleme/blob/master/docker-compose-deploy.yaml) that you can use to generate a docker image with for ConsoleMe. You'll need to craft your own ConsoleMe configuration.

## Deploy with AWS CDK \(AWS Cloud Development Kit\)

ConsoleMe has [example CDK files ](https://github.com/Netflix/consoleme/tree/master/cdk) that can assist you with deploying ConsoleMe in a central account, and creating the roles that ConsoleMe needs in your spoke accounts. The central account configuration handles ACM \(for TLS certificates\), Route53, load balancing, DynamoDB tables, Redis cache, authentication via Cognito and configuration storage in S3 bucket.

