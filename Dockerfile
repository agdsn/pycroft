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
    && apt-get install -y --no-install-recommends \
        bash \
        curl \
        git \
        libpq-dev \
        libsqlite3-dev \
        nodejs \
        npm \
        python3-dev \
        python3-pip \
        # For compiling things in pip
        build-essential \
        sqlite3 \
        vim \
    && ln -s /usr/bin/nodejs /usr/bin/node \
    && npm install -g bower

# Install Python packages
COPY vagrant/requirements.txt /

# pip3 install -U pip installs an additional pip3 binary to
# `/usr/local/bin/pip3` as opposed to the OS-owned `/usr/bin/pip3`.
# Removal of the hash table with `hash -r` is thus necessary to tell
# the bash that the new, up-to-date binary exists.
RUN pip3 install -U pip \
    && hash -r \
    && pip3 install -r /requirements.txt

RUN adduser --disabled-password --gecos "Application" pycroft
RUN mkdir -p $PROJECT_DIR/ && chown pycroft:pycroft $PROJECT_DIR

# Installing the js dependencies via bower cannot be done as root
COPY bower.json .bowerrc $PROJECT_DIR/
RUN export BOWER_DIR=$PROJECT_DIR/web/static/libs/ \
    && mkdir -p $BOWER_DIR \
    && chown pycroft:pycroft $BOWER_DIR \
    && cd $PROJECT_DIR/ \
    && echo "Installing js dependencies." \
    && bower --allow-root install -F \
    && bower --allow-root update -F

COPY . $PROJECT_DIR

RUN chown -R pycroft:pycroft $PROJECT_DIR

USER pycroft
WORKDIR $PROJECT_DIR

EXPOSE 5000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["./server_run.py", "--debug", "--exposed"]
