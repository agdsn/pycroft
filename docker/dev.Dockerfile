# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM agdsn/pycroft-base

USER root
WORKDIR /

COPY etc/apt /etc/apt

# Install Debian packages
# Build-essential is needed For compiling things in pip
# the curl is necessary because yarn devs are fancy enough to use a CI
# but the don't care for updating their keys. I'm raging.
RUN apt-key add /etc/apt/keys/nodesource.gpg.key \
    && apt-key add /etc/apt/keys/yarnpkg.gpg.key \
    && ( curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - ) \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        bash-completion \
        build-essential \
        curl \
        gdb \
        git \
        less \
        libpq-dev \
        nodejs \
        postgresql-client \
        strace \
        unzip \
        vim \
        yarn \
    && apt-get clean

COPY . /

USER pycroft
WORKDIR /opt/pycroft

EXPOSE 5000

CMD ["http"]
