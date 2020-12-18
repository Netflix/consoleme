# Required IAM Permissions

By now, you should have the ConsoleMe web UI running, though it probably can't do much at the moment. This is where you'll need to configure ConsoleMe for your environment. The ConsoleMe service needs its own user/role \(with an InstanceProfile for EC2 deployment\), and each of your accounts should have a role that ConsoleMe can assume into.

