# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM debian:wheezy
MAINTAINER Sebastian Schrader <sebastian.schrader@wh2.tu-dresden.de>
ENV PROJECT_DIR=/pycroft LANG=en_US.utf8 DEBIAN_FRONTEND=noninteractive

COPY etc/apt/sources.list /etc/apt/sources.list

# Setup locale
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/g' /etc/locale.gen && \
    locale-gen && \
    dpkg-reconfigure locales

# Install Debian packages
RUN apt-get update && \
    apt-get -y install \
        bash \
        curl \
        git \
        libpq-dev \
        libsqlite3-dev \
        nodejs \
        openssh-server \
        postgresql \
        postgresql-client \
        python-dev \
        python-pip \
        sqlite3 \
        sudo \
        supervisor \
        sysv-rc \
        sysvinit-utils \
        vim && \
    ln -s /usr/bin/nodejs /usr/bin/node

# Install NPM
RUN curl -s -L https://npmjs.org/install.sh | sh

# Install Bower
RUN npm install -g bower

# Install Python packages
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Add vagrant user
COPY home/vagrant/ /home/vagrant/
COPY etc/profile.d/ /etc/profile.d/
COPY etc/sudoers.d/ /etc/sudoers.d/
COPY defaults /etc/defaults/vagrant
RUN . /etc/defaults/vagrant && \
    groupadd --force --gid $VAGRANT_GID vagrant
RUN . /etc/defaults/vagrant && \
    useradd --no-create-home --uid $VAGRANT_UID --gid $VAGRANT_GID --shell /bin/bash vagrant && \
    chown -R $VAGRANT_UID:$VAGRANT_GID /home/vagrant

COPY usr/local/bin/ /usr/local/bin/
COPY etc/supervisor/ /etc/supervisor

RUN mkdir /var/run/sshd

VOLUME ["/pycroft"]
EXPOSE 22 5000 5432
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
