#!/bin/bash

# Execute a command protected by a lock on a given directory.
#
# The directory is assumed to exist.
#
# $1: path to directory on which to obtain a lock
# $@: command (anything executable by bash)
function execute_with_dirlock() {
  local -r lockdir="$1"
  shift

  # creates file descriptor $lockfd
  exec {lockfd}<"$lockdir"

  # Σ times ≥ 5min, should be enough for most purposes.
  for wait_s in 1 1 1 2 5 10 15 30 30 30 30 30 30 30 30 30; do
    echo -n "Trying to obtain lock on ${lockdir} (timeout=${wait_s}s)... "
    if flock --exclusive --wait $wait_s $lockfd; then

      # success, execution
      echo -e "Success!\nStarting execution."
      "$@"

      return 0
    fi;
    echo "Failed!"
  done

  echo "Maximum retries exceeded. Giving up."
  return 1
}
