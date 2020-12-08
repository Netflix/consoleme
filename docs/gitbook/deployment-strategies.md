# Deployment Strategies

Each organization is different in how they would wish to deploy ConsoleMe, and which specific operating system or base image they would want to deploy ConsoleMe on. We don't currently support or recommend any specific deployment flows. But we have a few resources that might help you get started. Help is definitely wanted in this area, so please contribute if you have guidance in this area.

## Create an Amazon AMI to deploy manually

ConsoleMe includes an example Packer configuration to assist with creating an image. You'll want to craft a custom configuration for ConsoleMe before creating an image, or be prepared to SSH into the instance you create to debug. Also ensure that you have [Packer installed](https://learn.hashicorp.com/tutorials/packer/getting-started-install).

To create an image with Packer, run the following command in the ConsoleMe repository:

`make create_ami`

## Deploy with Terraform

ConsoleMe has [example Terraform files ](https://github.com/Netflix/consoleme/tree/master/terraform)that can assist you with deploying ConsoleMe in a central account, and creating the roles that ConsoleMe needs in your spoke accounts. 

The central account configuration does not currently handle ACM \(for TLS certificates\), Route53, or load balancing.





