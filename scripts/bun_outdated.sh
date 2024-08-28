#!/bin/bash
FORCE_COLOR=1 bun outdated | \
  sed -E \
    -e 's/│/|/g' \
    -e 's/\x1b\[1m(\x1b\[[0-9;]+m)+([0-9.]+)\x1b\[0m/**\2**/g' \
    -e 's/\x1b\[[0-9;]+m//g' \
    -e '2a| --- | --- | --- | --- |' \
    -e '/─/d'
