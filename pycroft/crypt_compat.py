# Copyright (c) 2026 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""Restore ``crypt`` for passlib on Python ≥ 3.13 (PEP 594).

Import this module before any ``passlib`` import. ``passlib.utils`` probes
``crypt`` at import time and caches failure forever if it is missing.
"""

from __future__ import annotations

import sys

import legacycrypt

sys.modules.setdefault("crypt", legacycrypt)
