#!/bin/bash -l
# Execute a login shell to prime the environment

# This entrypoint installs the javascript libraries if necessary.
# Although the dockerfile takes care off setting them up in the
# container's file system, it is common practise to mount the
# developer's project directory from the host into the container,
# which doesn't contain said libraries yet.

if [ -f ./.bowerrc ]; then
    js_libs_dir=$(sed -n -e 's/^.*"directory": "\(.*\)",.*$/\1/p' .bowerrc)

    if [ ! -d $js_libs_dir ]; then
        # TODO: add comment
        echo "Didn't find $js_libs_dir, bootstrapping js libraries"
        bower install -F
        bower update -F
    fi
fi

exec "$@"
