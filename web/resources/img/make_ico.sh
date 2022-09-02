#!/bin/bash
set -euo pipefail

require() {
  if ! [[ -x $(command -v "$1") ]]; then
      echo "command $1 required. Please install the required package. exiting."
      exit 255
  fi
}

mkpng() {
    echo "creating $1x$1 png version (pycroft.$1.png)..."
    inkscape -w "$1" -h "$1" -o "pycroft.$1.png" pycroft.svg
    echo "...done"
}

require inkscape
require convert
mkpng 16
mkpng 32
echo "Converting to .ico..."
convert pycroft.*.png favicon.ico
rm pycroft.*.png
echo "...done. New contents:"
identify favicon.ico
