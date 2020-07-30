output "public_ip" {
  description = "The public IP address of the EC2 instance running the application."
  value       = module.server.public_ip
}