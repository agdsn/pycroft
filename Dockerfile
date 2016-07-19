# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM debian:jessie
ENV PROJECT_DIR=/pycroft LANG=en_US.UTF-8 DEBIAN_FRONTEND=noninteractive

COPY vagrant/etc/apt/sources.list /etc/apt/sources.list

# Setup locale
RUN apt-get update \
    && apt-get install -y locales \
    && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && dpkg-reconfigure locales \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Install Debian packages
RUN apt-get update \
    && apt-get -y install \
        bash \
        curl \
        git \
        libpq-dev \
        libsqlite3-dev \
        nodejs \
        npm \
        python-dev \
        python-pip \
        sqlite3 \
        sudo \
        vim \
    && ln -s /usr/bin/nodejs /usr/bin/node

# Install Bower
RUN npm install -g bower

# Install Python packages
COPY vagrant/requirements.txt /
RUN pip install -r /requirements.txt

RUN adduser --disabled-password --gecos "Application" pycroft
RUN mkdir -p $PROJECT_DIR/ && chown -R pycroft:pycroft $PROJECT_DIR/
USER pycroft

# Installing the js dependencies via bower cannot be done as root
COPY bower.json .bowerrc $PROJECT_DIR/
RUN mkdir -p $PROJECT_DIR/web/static/libs/

COPY . $PROJECT_DIR

WORKDIR $PROJECT_DIR

RUN echo "Installing js dependencies." \
    && bower install -F \
    && bower update -F

EXPOSE 5000
CMD ["./server_run.py", "--debug", "--exposed"]
