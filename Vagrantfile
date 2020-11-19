# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
#
# Install docker-compose plugin: vagrant plugin install vagrant-docker-compose
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-16.04"
  config.vm.synced_folder ".", "/apps/consoleme"
  # TODO: Make this OSS?
  config.vm.synced_folder "../consoleme-internal", "/apps/consoleme-internal"
  config.vm.synced_folder "~/.config/pip", "/home/vagrant/.config/pip"
  config.vm.synced_folder "~/.ssh", "/home/vagrant/.ssh"
  config.vm.synced_folder "~/.metatron", "/home/vagrant/.metatron"
  config.vm.network "forwarded_port", guest: 22, host: 2222
  # config.ssh.username = 'vagrant'
  # config.ssh.password = 'vagrant'
  #

  config.vm.provision "shell", inline: <<-SHELL
    apt-get -qq update
    apt-get --allow-unauthenticated update && apt-get --allow-unauthenticated install -y \
    software-properties-common
    add-apt-repository ppa:deadsnakes/ppa
    apt-get --allow-unauthenticated update && apt-get --allow-unauthenticated install -y \
    python3.8 \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    python3-pip \
    python3.8-venv \
    libpython3.8 \
    git
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    add-apt-repository \
      "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) \
      stable"
    apt-get update
    apt-get --allow-unauthenticated install -y docker-ce docker-ce-cli containerd.io
    python3.8 -m venv /apps/env
    /apps/env/bin/pip install --upgrade pip
    /apps/env/bin/pip install --upgrade pip-tools
    /apps/env/bin/pip install --upgrade setuptools
    /apps/env/bin/pip install docker-py
    . /apps/env/bin/activate; pip install -e /apps/consoleme-internal; cd /apps/consoleme; pip install -e .; pip install -r /apps/consoleme/requirements.txt; pip install -r /apps/consoleme/requirements-test.txt
    systemctl start docker
    systemctl enable docker
    curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    cd /apps/consoleme
    mkdir -p /data
    mkdir -p /ddbdata
    docker-compose up -d
  SHELL
end
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://vagrantcloud.com/search.

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # NOTE: This will enable public access to the opened port
  # config.vm.network "forwarded_port", guest: 80, host: 8080
  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine and only allow access
  # via 127.0.0.1 to disable public access
  # config.vm.network "forwarded_port", guest: 80, host: 8080, host_ip: "127.0.0.1"

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  # config.vm.synced_folder "../data", "/vagrant_data"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  #
  # config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
  #   vb.memory = "1024"
  # end
  #
  # View the documentation for the provider you are using for more
  # information on available options.

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.
  # config.vm.provision "shell", inline: <<-SHELL
  #   apt-get update
  #   apt-get install -y apache2
  # SHELL
