# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

FROM agdsn/pycroft-dev AS builder

WORKDIR /opt/pycroft/app

# Download or build wheels of requirements
COPY --chown=pycroft:pycroft requirements.txt .
RUN /opt/pycroft/venv/bin/pip wheel --wheel-dir /opt/pycroft/wheel -r requirements.txt

# Download JS/CSS dependencies
COPY --chown=pycroft:pycroft package.json .
RUN yarn install --mutex network --network-concurrency 1

# Build Pycroft wheel
COPY --chown=pycroft:pycroft . .
RUN yarn run --prod build
RUN /opt/pycroft/venv/bin/pip wheel --no-deps --wheel-dir /opt/pycroft/wheel .

FROM agdsn/pycroft-base

# Install wheels from builder
COPY --chown=pycroft:pycroft --from=builder  /opt/pycroft/wheel /opt/pycroft/wheel
RUN /opt/pycroft/venv/bin/pip install /opt/pycroft/wheel/*.whl

EXPOSE 5000

CMD ["uwsgi"]
