# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
# -*- mode: ruby -*-
# vi: set ft=ruby :

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.provider "docker" do |d|
    d.create_args = ["--cap-add=SYS_ADMIN", "--security-opt=seccomp:unconfined"]
    d.build_dir = "vagrant/"
    d.build_args = ["--tag=agdsn/pycroft:latest"]
    d.has_ssh = true
  end

  config.vm.provider "virtualbox" do |vb, override|
      override.vm.box = "debian/jessie64"
  end

  #pycroft web and database server, built automatically
  config.vm.define "webdb", primary: true do |webdb|
    webdb.vm.provider "virtualbox" do |vb, override|
      vb.name = "pycroft-web-db"
      vb.memory = 512
      vb.cpus = 2
      override.vm.provision "provision", type: "shell", path: "vagrant/provision.sh"
    end

    webdb.vm.provider "docker" do |d|
      d.name = "pycroft-web-db"
      File.open('vagrant/defaults', 'w') do |file|
        file.puts("VAGRANT_UID=#{Process.uid}")
        file.puts("VAGRANT_GID=#{Process.gid}")
      end
    end

    webdb.vm.network :forwarded_port, host:5000, guest: 5000,
                     host_ip: "127.0.0.1", auto_correct: true
    webdb.vm.network :forwarded_port, host:5432, guest:5432,
                     host_ip: "127.0.0.1", auto_correct: true
  end
end
