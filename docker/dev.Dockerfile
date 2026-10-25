# syntax=docker/dockerfile:1
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM alpine:latest AS bunzipper
RUN --mount=type=cache,target=/var/cache/apk,sharing=locked \
    apk add unzip curl
RUN <<EOF ash
    set -euo pipefail
    curl -sSfLO https://github.com/oven-sh/bun/releases/download/bun-v1.4.4/bun-linux-x64-baseline.zip
    unzip -j bun-linux-x64-baseline.zip bun-linux-x64-baseline/bun -d /opt
    echo "10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235  /opt/bun" \
        | sha256sum -c -
EOF

# syntax=docker/dockerfile:1.4
FROM pycroft-base

USER root
WORKDIR /

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
        postgresql-client \
        strace \
        unzip \
        vim

# The test and dev containers bind-mount a checkout owned by the host user.
# Git refuses that directory, versioningit treats the refusal as "not a
# repository", and `uv sync` dies while building wtforms-widgets.
RUN git config --system --add safe.directory '*'
COPY --chmod=755 --from=bunzipper /opt/bun /usr/local/bin/bun

COPY --link . /
COPY --link --chmod=755 ./container /container

USER pycroft
WORKDIR /opt/pycroft

EXPOSE 5000

CMD ["http"]
