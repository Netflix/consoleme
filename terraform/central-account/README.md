# Demo infrastructure for ConsoleMe in AWS

Since Consoleme is not public yet, we have to load the code into an S3 bucket as a tar.gz file and then download it as part of the demo infrastructure.

* Create an AWS S3 bucket and note the name of the bucket. In this example, it is called `my-bucket`.

* Download and install Terraform 0.12.28. I highly recommend [tfenv](https://github.com/tfutils/tfenv)

* Create the tarball of Consoleme

```bash
make consoleme.tar.gz
```

* Copy the tarball to your bucket

```bash
aws s3 cp consoleme.tar.gz s3://my-bucket
```

* Create your `terraform.tfvars` file and insert the content shown below.

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

bucket = "my-bucket"
```

* Create the infrastructure with Terraform.

```bash
terraform init
terraform plan
terraform apply -auto-approve
```

The public IP is included in your output. You can then open up the demo environment at http://publicipaddressfromoutput:8081

* Once you are done, destroy the infrastructure:

```bash
terraform destroy -auto-approve
```
