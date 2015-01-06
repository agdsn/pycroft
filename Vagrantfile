# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
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
    webdb.vm.network :forwarded_port, host:5432, guest:5432,
                     host_ip: "127.0.0.1", auto_correct: true
    webdb.vm.provision "sw", type: "shell",
                     path: "vagrant/provision-sw.sh"
    webdb.vm.provision "db", type: "shell",
                     path: "vagrant/provision-db.sh"
  end
end
