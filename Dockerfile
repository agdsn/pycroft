# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM debian:jessie
ENV PROJECT_DIR=/pycroft LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive

COPY vagrant/ /

# Install Debian packages
# Build-essential is needed For compiling things in pip
RUN apt-key add /etc/nodesource.gpg.key && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        curl \
        git \
        libpq-dev \
        libsqlite3-dev \
        nodejs \
        python3-dev \
        python3-pip \
        build-essential \
        sqlite3 \
        vim \
    && npm install -g bower

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

RUN chown -R pycroft:pycroft $PROJECT_DIR \
    && pip install -e $PROJECT_DIR
# the latter installs pycroft in “develop” mode following `setup.py`.

USER pycroft
WORKDIR $PROJECT_DIR

EXPOSE 5000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["pycroft", "--debug", "--exposed"]
