output "public_ip" {
  description = "The public IP address of the EC2 instance running the application."
  value       = module.server.public_ip
}

output "zREADME" {
  value = <<README
# ------------------------------------------------------------------------------
# ConsoleMe Demo Guide
# ------------------------------------------------------------------------------

If you're following the Terraform demo environment and your Terraform apply was
successful, you can wait for a few minutes and then visit the ConsoleMe dashboard
at the following URL:

$ http://${module.server.public_ip[0]}:8081

If you want to access the server, make sure you add your private key to your
SSH agent:

$ ssh-add path/to/private_key.pem

Then SSH into the server:

$ ssh -A ec2-user@${module.server.public_ip[0]}

If you want to experiment with the ConsoleMe config, you can find the config files at the path:

$ cd /apps/consoleme/example_config/

README
}