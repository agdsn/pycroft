#!/bin/bash

# Try to close {lockfd} and remove lockfile.
#
# this function shall be called only after an `flock` command
#  has obtained a lock on the named file descriptor {lockfd}.
#
# {lockfd}: named file descriptor
# $1: lockfd
# $2: lockfile
function clean_lock() {
  local lockfd="$1" lockfile="$2"

  # closing the file descriptor to release the lock.  See `man 2 flock`.
  exec {lockfd}>&-

  # !!!! ATTENTION !!!!
  # `rm` without re-obtaining the lock causes the following to work ([A,B,C] =
  # Process A,B,C, resp.) without issues:
  # 1. [A] starts, obtains lock
  # 2. [B] starts, waits on lock
  # 3. [A] gets SIGINT or finishes
  #         …the `clean_lock` trap starts firing
  #         …the FD gets closed by `exec $LOCKFD>&-`, effectively releasing the lock
  # 3.. [B] immediately obtains lock
  # 3.. [A] …rm -f $lockfile runs, removes file without issues
  # 4. [A] exits
  # 5. [C] starts, obtains lock because $lockfile does not exist
  # INCONSISTENT STATE: [A] exited, [B] running, [C] running
  # therefore, we re-obtain the lock as per the next line.
  if flock --nonblock "$lockfile" --command "rm -f $lockfile"; then
    echo "Successfully removed ${lockfile}."
  else
    echo -n "Could not remove lock file ${lockfile}. "
    echo "Perhaps another process immediately obtained the lock."
  fi
}

# check whether the birth time of a given file exceeds a given age.
# $1 filename
# $2 maximum age in seconds
function _file_older_than() {
  local file="$1" max_age="$2"
  if [[ ! -e $file ]]; then
    return 1  # false
  fi;
  # stat: %W: unix timestamp of birth time
  # date: %s: current unix timestamp
  age=$(($(date +%s) - $(stat --format %W "$file")))
  if (( age > max_age )); then
    return 0  # true
  else
    return 1  # false
  fi
}

# execute a command protected by a lock file.
# $1: command (anything executable by bash)
# $2: lock file path
function execute_locked() {
  local cmd="$1" lockfile="$2"
  if _file_older_than "$lockfile" $((30*60)); then
    echo "Lock file $lockfile is older than 30m, probably left over."
    echo "Please remove it manually or retry later."
    return 1
  fi;

  # creates file descriptor $lockfd
  exec {lockfd}<>"$lockfile"

  # Σ times ≥ 5min, should be enough for most purposes.
  for wait_s in 1 1 1 2 5 10 15 30 30 30 30 30 30 30 30 30; do
    echo -n "Trying to obtain lock on ${lockfile} (timeout=${wait_s}s)... "
    if flock --exclusive --wait $wait_s $lockfd; then
      trap 'clean_lock "$lockfd" "$lockfile"; exit 1' SIGINT SIGTERM SIGHUP

      # success, execution
      echo -e "Success!\nStarting execution."
      $cmd

      # cleanup
      clean_lock "$lockfd" "$lockfile"
      return 0
    fi;
    echo "Failed!"
  done

  echo "Maximum retries exceeded. Giving up."
  return 1
}
