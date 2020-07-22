#!/usr/bin/env bash
set -x

export HOME=/root
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

mkdir -p /apps/consoleme
mkdir /logs
cd /apps/
yum -y install unzip
aws s3 cp s3://${bucket}/consoleme.tar.gz /apps/
tar -xzvf consoleme.tar.gz -C consoleme/
rm consoleme.tar.gz

#### User specific installation
# Create a dedicated service user
useradd -r -s /bin/false consoleme
usermod -aG consoleme consoleme
usermod -aG docker consoleme

# Flower
useradd -r -s /bin/false flower
usermod -aG flower flower
mkdir -p /apps/flower
chown -R flower:flower /apps/flower
python3 -m venv /apps/flower/env --copies
source /apps/flower/env/bin/activate
pip install flower redis

# Set up a new Virtualenv in the Consoleme directory
python3 -m venv /apps/consoleme/env
source /apps/consoleme/env/bin/activate
chown -R consoleme:consoleme /apps/consoleme
chown -R consoleme:consoleme /logs
# Install it
cd /apps/consoleme
pip install xmlsec

make env_install

make dynamo
sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum-config-manager --enable epel
yum -y install redis
systemctl status redis
systemctl start redis
python /apps/consoleme/scripts/initialize_redis_oss.py

# Update the UI
cd /apps/consoleme

# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh > /tmp/nvm-install.sh
chmod +x /tmp/nvm-install.sh
bash /tmp/nvm-install.sh
echo 'export NVM_DIR="/root/.nvm"' >> /root/.bashrc
echo '[ -s "\$NVM_DIR/nvm.sh" ] && . "\$NVM_DIR/nvm.sh"  # This loads nvm' >> /root/.bashrc
. ~/.nvm/nvm.sh
. ~/.bashrc
cd /apps/consoleme
nvm install 12.18.2
nvm use 12.18.2
node -e "console.log('Running Node.js ' + process.version)"
npm install yarn -g
yarn
yarn install
/apps/consoleme/node_modules/webpack/bin/webpack.js --progress

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
Environment=CONFIG_LOCATION=/apps/consoleme/example_config/example_config_terraform.yaml
WorkingDirectory=/apps/consoleme
Type=simple
Restart=always
RestartSec=1
User=consoleme
Group=consoleme
ExecStart=/usr/bin/env /apps/consoleme/env/bin/python /apps/consoleme/consoleme/__main__.py

[Install]
WantedBy=multi-user.target
EOF

cat << EOF > /etc/systemd/system/celery.service
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=consoleme
Group=consoleme
Type=simple
Restart=always
RestartSec=1
WorkingDirectory=/apps/consoleme
Environment=CONFIG_LOCATION=/apps/consoleme/example_config/example_config_terraform.yaml
ExecStart=/usr/bin/env /apps/consoleme/env/bin/python /apps/consoleme/env/bin/celery -A consoleme.celery.celery_tasks worker --loglevel=info -l DEBUG -B

[Install]
WantedBy=multi-user.target
EOF

cat << EOF > /apps/consoleme/example_config/example_config_terraform.yaml
${demo_config}
EOF

# TODO: Remove this hacky way of removing the fake account ID... instead, stash the rendered template config in an S3 bucket and pull it from userdata
grep -rl '123456789012' /apps/consoleme/example_config/example_config_terraform.yaml | xargs sed -i "s/123456789012/${current_account_id}/g"
# Change permissions on service file
chown root:root /etc/systemd/system/celery.service
chmod 644 /etc/systemd/system/celery.service
chown root:root /etc/systemd/system/consoleme.service
chmod 644 /etc/systemd/system/consoleme.service

systemctl daemon-reload

mkdir -p /home/consoleme
chown consoleme:consoleme /home/consoleme/

# Make sure it is listed
systemctl list-unit-files | grep celery.service
systemctl list-unit-files | grep consoleme.service
# Enable the service and create the symlink in /usr/lib
systemctl start celery
systemctl enable celery
systemctl enable consoleme
systemctl start consoleme
