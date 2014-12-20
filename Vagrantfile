# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder ".", "/pycroft"

  # Don't create /vagrant
  config.vm.synced_folder ".", "/vagrant", disabled: true

  #pycroft web and database server, built automatically
  config.vm.define "webdb", primary: true do |webdb|
    webdb.vm.box = "chef/debian-7.6"
    webdb.vm.provider "virtualbox" do |vb|
      vb.name = "pycroft-web-db"
    end
    webdb.vm.network :forwarded_port, host:5000, guest: 5000,
                     host_ip: "127.0.0.1", auto_correct: true
    webdb.vm.provision :shell, path: "vagrant/webdb-provision.sh"
  end

  #Required once DB and web server are separate:
  # Create a private network, which allows host-only access to the machine
  #  using a specific IP.
  #  config.vm.network "private_network", ip: "192.168.33.10"
  # Create a public network, which generally matched to bridged network.
  #  Bridged networks make the machine appear as another physical device on
  #  your network.
  #  config.vm.network "public_network"  

=begin
  #pycroft web server, build automatically
  config.vm.define "web", autostart: false do |web|
    web.vm.box = "chef/debian-7.6"
    web.vm.provider "virtualbox" do |vb|
      vb.name = "pycroft-web"
    end
    web.vm.network :forwarded_port, host:5000, guest: 5000,
                   host_ip: "127.0.0.1", auto_correct: true
    web.vm.provision :shell, inline: "echo Not implemented yet...; exit 1"
  end

  #pycroft database server, build automatically
  config.vm.define "db", autostart: false do |db|
    db.vm.box = "chef/debian-7.6"
    db.vm.provider "virtualbox" do |vb|
      vb.name = "pycroft-db"
    end
    db.vm.network :forwarded_port, host:5432, guest: 5432,
                  host_ip: "127.0.0.1"
    db.vm.provision :shell, inline: "echo Not implemented yet...; exit 1"
  end
=end

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # If true, then any SSH connections made will enable agent forwarding.
  # Default value: false
  # config.ssh.forward_agent = true

  #config.vm.provider "virtualbox" do |vb|
  #  vb.gui = false
  #  vb.name = "pycroft-vm"
  #  # Use VBoxManage to customize the VM. For example to change memory:
  #  # vb.customize ["modifyvm", :id, "--memory", "1024"]
  #end  
  
  # Enable provisioning with CFEngine. CFEngine Community packages are
  # automatically installed. For example, configure the host as a
  # policy server and optionally a policy file to run:
  #
  # config.vm.provision "cfengine" do |cf|
  #   cf.am_policy_hub = true
  #   # cf.run_file = "motd.cf"
  # end
  #
  # You can also configure and bootstrap a client to an existing
  # policy server:
  #
  # config.vm.provision "cfengine" do |cf|
  #   cf.policy_server_address = "10.0.2.15"
  # end
end
