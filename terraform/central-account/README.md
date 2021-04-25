# Demo infrastructure for ConsoleMe in AWS

- Download and install Terraform latest. We highly recommend [tfenv](https://github.com/tfutils/tfenv)

  - If using tfenv, run the following commands in the `central_account` directory:
    - `tfenv install latest`
    - `tfenv use latest`

- Create your `terraform.tfvars` file (see [terraform.tfvars.example](terraform.tfvars.example) for direction) and
  insert the content shown below.

> **Important**: Then make sure that the bucket `my-bucket` is reflected in your `terraform.tfvars` file.

```hcl-terraform
name = "consoleme"
stage = "somestage"
namespace = "sfdc"
region = "us-east-1"
default_tags = {}
key_name = "kinnaird"
vpc_cidr = "10.1.1.0/24"
server_subnet_cidrs = [
  "10.1.1.0/28"]
subnet_azs = [
  "us-east-1a"]
consoleme_repo = "https://github.com/Netflix/consoleme" # Optionally customize this with a specific release by appending --branch <version>
allowed_inbound_cidr_blocks = []  # NOTE: Do not open this up to 0.0.0.0/0. Restrict access to your IP address until you've configured authentication securely.

bucket_name_prefix = "your-name-prefix"
```

- Create the infrastructure with Terraform.

```bash
terraform init # If you're upgrading from a previous version of Terraform, you may need to run `terraform init -upgrade`
terraform plan
terraform apply -auto-approve
```

- Important: the template uses a private subnet by default to avoid any uncomfortable mishaps. There's a load balancer
  in the code that provides the bridge from the Internet into the private network, and directly to the ConsoleMe server.
  The load balancer is internal-only by default. Change the allow_internet_access variable to true to allow access.

- This server needs authentication to be used properly. In this Terraform example, we've opted to use ALB
  authentication. The ALB Authentication is set up as part of the Terraform, with variables provided in
  the `terraform.tfvars` you should create. ConsoleMe supports other methods of authentication, please see examples
  under [example_config](../example_config).

- After deployment, you can wait for a few minutes and then visit the ConsoleMe dashboard at the URL included in the
  output.

The public address of the load balancer is included in your output. You can then open up the demo environment
at https://publiciaddressfromoutput:8081

- Once you are done, destroy the infrastructure:

```bash
terraform destroy -auto-approve
```
