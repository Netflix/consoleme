# Demo infrastructure for ConsoleMe in AWS

Since Consoleme is not public yet, we have to create a tar.gz file in the root directory, have Terraform upload the tarball to an S3 bucket, and then download it as part of the demo infrastructure.

- First, create the tarball of Consoleme in the root directory of this repository.

```bash
make consoleme.tar.gz
```

Note that if you modify this consoleme.tar.gz file and then run Terraform again, it will update the Terraform infrastructure to include your changes.

- Download and install Terraform 0.12.28. I highly recommend [tfenv](https://github.com/tfutils/tfenv)

- Create your `terraform.tfvars` file and insert the content shown below.

> **Important**: Then make sure that the bucket `my-bucket` is reflected in your `terraform.tfvars` file.

```hcl-terraform
name                = "consoleme"
stage               = "somestage"
namespace           = "sfdc"
region              = "us-east-1"
default_tags        = {}
key_name            = "kinnaird"
vpc_cidr            = "10.1.1.0/24"
public_subnet_cidrs = ["10.1.1.0/28"]
subnet_azs          = ["us-east-1a"]

allowed_inbound_cidr_blocks = []  # NOTE: Do not open this up to 0.0.0.0/0. Restrict access to your IP address for the demo.

bucket_name_prefix = "your-name-prefix"
```

- Create the infrastructure with Terraform.

```bash
terraform init
terraform plan
terraform apply -auto-approve
```

- You can wait for a few minutes and then visit the ConsoleMe dashboard
  at the URL included in the output. Note that the output also provides instructions on

The public IP is included in your output. You can then open up the demo environment at http://publicipaddressfromoutput:8081

- Once you are done, destroy the infrastructure:

```bash
terraform destroy -auto-approve
```
