#!/usr/bin/env bash
set -x

# ---------------------------------------------------------------------------------------------------------------------
# Filter out useless messages from logs
# ---------------------------------------------------------------------------------------------------------------------
cat <<EOF > /etc/rsyslog.d/01_filters.conf

if \$programname == 'systemd' and \$msg contains "Started Session" then stop
if \$programname == 'systemd' and \$msg contains "Starting Session" then stop
if \$programname == 'systemd' and \$msg contains "Created slice" then stop
if \$programname == 'systemd' and \$msg contains "Starting user-" then stop
if \$programname == 'systemd' and \$msg contains "Stopping user-" then stop
if \$programname == 'systemd' and \$msg contains "Removed slice" then stop
EOF
systemctl restart rsyslog

# ---------------------------------------------------------------------------------------------------------------------
# Prereqs
# ---------------------------------------------------------------------------------------------------------------------

# Install Docker
sudo yum update -y
yum -y install git python3 python3-pip  python3-devel
yum -y install libcurl-devel
yum -y install libxml2-devel xmlsec1-devel xmlsec1-openssl-devel libtool-ltdl-devel
sudo yum install -y gcc-c++

yum -y install gcc
sudo amazon-linux-extras install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# TODO: Copy over the directory
mkdir -p /apps/
cd /apps/
yum -y install unzip
aws s3 cp s3://${bucket}/consoleme.tar.gz /apps/
tar -xzvf consoleme.tar.gz
rm consoleme.tar.gz

#### User specific installation
# Create a dedicated service user
useradd -r -s /bin/false consoleme
#groupadd consoleme
# Add users to the consoleme group
usermod -aG consoleme consoleme
usermod -a -G docker consoleme

# Set up a new Virtualenv in the Consoleme directory
python3 -m venv /apps/consoleme/env
# Activate the virtualenv
source /apps/consoleme/env/bin/activate
# Make sure the consoleme user owns it, not root
chown -R consoleme:consoleme /apps/consoleme
# Install it
cd /apps/consoleme
pip install xmlsec

make env_install

make dynamodb
sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum-config-manager --enable epel
yum -y install redis
systemctl status redis
systemctl start redis
python /apps/consoleme/scripts/initialize_redis_oss.py

#make bootstrap
# Since the setup ran as root, just chown it again so the consoleme user owns it
chown -R consoleme:consoleme /apps/consoleme

cat << EOF > /etc/systemd/system/consoleme.service
[Unit]
Description=ConsoleMe Service
After=network.target
StartLimitIntervalSec=0
StartLimitBurst=5
StartLimitIntervalSec=0

[Service]
#Environment=CONFIG_LOCATION=/apps/consoleme/docker/example_config_alb_auth.yaml
Environment=CONFIG_LOCATION=/apps/consoleme/example_config/example_config_development.yaml
WorkingDirectory=/apps/consoleme
Type=simple
Restart=always
RestartSec=1
User=consoleme
ExecStart=/usr/bin/env /apps/consoleme/env/bin/python /apps/consoleme/consoleme/__main__.py

[Install]
WantedBy=multi-user.target
EOF


# Change permissions on service file
chown root:root /etc/systemd/system/consoleme.service
chmod 644 /etc/systemd/system/consoleme.service
# Make sure it is listed
systemctl list-unit-files | grep consoleme.service
# Enable the service and create the symlink in /usr/lib
systemctl enable consoleme
systemctl start consoleme