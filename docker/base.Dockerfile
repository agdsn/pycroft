# syntax=docker/dockerfile:1.4
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

FROM python:3.12-slim-bookworm
ARG UID=1000
ARG GID=1000
ENV LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive

COPY etc/apt /etc/apt
COPY --from=ghcr.io/astral-sh/uv:0.6.2 /uv /uvx /usr/local/bin/

# Install Debian packages
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        bash \
        libpq5 \
    && apt-get clean

RUN groupadd --force --gid $GID pycroft \
    && useradd --non-unique --home-dir /opt/pycroft --create-home --uid $UID --gid $GID --comment "Application" pycroft

USER pycroft
WORKDIR /opt/pycroft

# - Create a virtual environment
# - Upgrade pip, setuptools and wheel
# - Create app directory
ENV VIRTUAL_ENV=/opt/pycroft/venv
RUN --mount=type=cache,target=/opt/pycroft/.cache,uid=$UID,gid=$GID\
    uv venv /opt/pycroft/venv \
    && uv pip install pip \
    && mkdir /opt/pycroft/app /opt/pycroft/wheel

COPY --link . /

ENTRYPOINT ["/container/entrypoint"]
