#!/usr/bin/env bash
set -x

export HOME=/root
export EC2_REGION=${region}
export CONFIG_LOCATION=${CONFIG_LOCATION}
export CONSOLEME_CONFIG_S3=${CONSOLEME_CONFIG_S3}

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
yum -y erase python3
sudo amazon-linux-extras enable python3.8 # consoleme requires 3.8
yum -y install git python3.8 python38-pip python38-devel
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
git clone {consoleme_repo}

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
python3.8 -m venv /apps/flower/env --copies
source /apps/flower/env/bin/activate
pip3.8 install flower redis

# Set up a new Virtualenv in the Consoleme directory
python3.8 -m venv /apps/consoleme/env
source /apps/consoleme/env/bin/activate
chown -R consoleme:consoleme /apps/consoleme
chown -R consoleme:consoleme /logs
# Install it
cd /apps/consoleme
pip3.8 install xmlsec

# Make uses "pip" and "python", assuming they are 3.8, but they actually point to python2 (because yum uses it)
alias python=python3.8
alias pip=pip3.8
make env_install

make dynamo
unalias python
unalias pip

sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum-config-manager --enable epel
yum -y install redis
systemctl status redis
systemctl start redis

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
yarn --cwd ui
yarn --cwd ui build:prod

# Since the setup ran as root, just chown it again so the consoleme user owns it
chown -R consoleme:consoleme /apps/consoleme
chown -R consoleme:consoleme /logs/consoleme

cat << EOF > /etc/environment
EC2_REGION=${region}
CONFIG_LOCATION=${CONFIG_LOCATION}
CONSOLEME_CONFIG_S3=${CONSOLEME_CONFIG_S3}
EOF

cat << EOF > /etc/systemd/system/consoleme.service
[Unit]
Description=ConsoleMe Service
After=network.target
StartLimitIntervalSec=0
StartLimitBurst=5
StartLimitIntervalSec=0

[Service]
Environment=EC2_REGION=${region}
Environment=CONFIG_LOCATION=${CONFIG_LOCATION}
WorkingDirectory=/apps/consoleme
Type=simple
Restart=always
RestartSec=1
User=consoleme
Group=consoleme
ExecStart=/usr/bin/env /apps/consoleme/env/bin/python3.8 /apps/consoleme/consoleme/__main__.py

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
Environment=CONFIG_LOCATION=${CONFIG_LOCATION}
Environment=EC2_REGION=${region}
ExecStart=/usr/bin/env /apps/consoleme/env/bin/python3.8 /apps/consoleme/env/bin/celery -A consoleme.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=15

[Install]
WantedBy=multi-user.target
EOF

cat << EOF >> /root/.bashrc
export CONFIG_LOCATION=${CONFIG_LOCATION}
export CONSOLEME_CONFIG_S3=${CONSOLEME_CONFIG_S3}
export EC2_REGION=${region}
EOF

# TODO: Remove this hacky way of removing the fake account ID... instead, stash the rendered template config in an S3 bucket and pull it from userdata
grep -rl '123456789012' "${CONFIG_LOCATION}" | xargs sed -i "s/123456789012/${current_account_id}/g"
# Change permissions on service file
chown root:root /etc/systemd/system/celery.service
chmod 644 /etc/systemd/system/celery.service
chown root:root /etc/systemd/system/consoleme.service
chmod 644 /etc/systemd/system/consoleme.service

systemctl daemon-reload

mkdir -p /home/consoleme
chown consoleme:consoleme /home/consoleme/

cat << EOF >> /home/consoleme/.bashrc
export CONFIG_LOCATION=${CONFIG_LOCATION}
export EC2_REGION=${region}
EOF

# Run script to decode and write a custom ConsoleMe configuration. This won't do anything unless CONSOLEME_CONFIG_S3 is defined.
sudo -u consoleme bash -c '. /home/consoleme/.bashrc ; /apps/consoleme/env/bin/python3.8 /apps/consoleme/scripts/retrieve_or_decode_configuration.py'
# Make sure it is listed
systemctl list-unit-files | grep celery.service
systemctl list-unit-files | grep consoleme.service
# Enable the service and create the symlink in /usr/lib
systemctl start celery
systemctl enable celery
systemctl enable consoleme
systemctl start consoleme

sudo -u consoleme bash -c '. /home/consoleme/.bashrc ; /apps/consoleme/env/bin/python3.8 /apps/consoleme/scripts/initialize_redis_oss.py'

echo "Running custom userdata script"
${custom_user_data_script}