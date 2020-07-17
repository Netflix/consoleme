# Demo infrastructure for ConsoleMe in AWS

Since Consoleme is not public yet, we have to load the code into an S3 bucket as a tar.gz file and then download it as part of the demo infrastructure.

```bash
make consoleme.tar.gz
aws s3 cp consoleme.tar.gz s3://my-bucket
```

Then make sure that the bucket `my-bucket` is reflected in your terraform.tfvars.

* Create your terraform.tfvars
* terraform init, plan, and apply

Right now, this spins up the instance, but it does not