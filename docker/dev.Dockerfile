# syntax=docker/dockerfile:1.4
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM pycroft-base

USER root
WORKDIR /

COPY etc/apt /etc/apt

# Install Debian packages
# Build-essential is needed For compiling things in pip
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
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
        npm \
        postgresql-client \
        strace \
        unzip \
        vim \
    && apt-get clean

COPY --link . /
COPY --link --chmod=755 ./container /container

USER pycroft
WORKDIR /opt/pycroft

EXPOSE 5000

CMD ["http"]
