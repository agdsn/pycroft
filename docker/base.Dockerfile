# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

FROM debian:jessie
ARG UID=1000
ARG GID=1000
ENV LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive

COPY etc/apt /etc/apt

# Install Debian packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        libpq5 \
        python3 \
        python3-venv \
        uwsgi-plugin-python3 \
    && apt-get clean

RUN groupadd --force --gid $GID pycroft \
    && useradd --non-unique --home-dir /opt/pycroft --create-home --uid $UID --gid $GID --comment "Application" pycroft

USER pycroft
WORKDIR /opt/pycroft

# - Create a virtual environment
# - Upgrade pip, setuptools and wheel
# - Create app directory
RUN python3 -m venv /opt/pycroft/venv \
    && /opt/pycroft/venv/bin/pip install -U pip setuptools wheel \
    && mkdir /opt/pycroft/app /opt/pycroft/wheel

COPY . /

ENTRYPOINT ["/container/entrypoint"]
