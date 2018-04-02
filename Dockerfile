# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
FROM debian:jessie
ARG UID=1000
ARG GID=1000
ENV PROJECT_DIR=/pycroft LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive

COPY vagrant/ /

# Install Debian packages
# Build-essential is needed For compiling things in pip
RUN apt-key add /etc/nodesource.gpg.key && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        curl \
        git \
        libpq-dev \
        nodejs \
        python3-dev \
        python3-venv \
        vim \
    && apt-get clean \
    && npm install -g bower

RUN groupadd --force --gid $GID pycroft \
    && useradd --non-unique --home-dir $PROJECT_DIR --create-home --uid $UID --gid $GID --comment "Application" pycroft \
    && mkdir -p /opt/venv && chown pycroft:pycroft /opt/venv

USER pycroft
WORKDIR $PROJECT_DIR

COPY --chown=pycroft:pycroft . .

# - Create a virtual environment
# - Upgrade pip, setuptools and wheel
# - Install requirements and pycroft in editable mode
# - Install JavaScript/CSS/HTML requirements with Bower
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install -U pip setuptools wheel \
    && /opt/venv/bin/pip install -r /requirements.txt -e . \
    && bower install -F \
    && bower update -F

EXPOSE 5000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["pycroft", "--debug", "--exposed"]
