#!/bin/bash
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

_check_context() {
    if [[  -z $1 && -z $DOCKER_CACHE_FILE ]]; then
        echo "Please provide a parameter or DOCKER_CACHE_FILE."
        exit 1
    fi
}

_env_or_param() {
    if [[ -z $1 && -n $DOCKER_CACHE_FILE. ]]; then
        echo $DOCKER_CACHE_FILE
        return
    fi
    echo $1
}

load_cache() {  # cache_file
    _check_context $@
    local cache_file=$(_env_or_param $@)
    echo "After local. cache_file is $cache_file"

    if [[ -f "$cache_file" ]]; then
        echo "Unpacking cache file $cache_file"
        gunzip -c "$cache_file" | docker load || echo Cache loading failed
    else
        echo "ERROR: Cache file $cache_file does not exist."
        exit 255
    fi
}

save_cache() {  # cache_file
    if [[ -z $DOCKER_IMAGE_NAME ]]; then
        local image=agdsn/pycroft-base
    else
        local image=$DOCKER_IMAGE_NAME
    fi

    _check_context $@
    local cache_file=$(_env_or_param $@)

    local images=$(docker history -q $image | sort  | uniq  | grep -v missing)
    echo "Attempting to save $images"
    docker save $images | gzip > $cache_file
}

if [[ $1 =~ ^(load_cache|save_cache)$ ]]; then
    $@
else
    echo -e "ERROR: Invalid command."
    echo "Usage: load_cache|save_cache"
    echo "The file can be applied as an argument or via DOCKER_CACHE_FILE."
    exit 1
fi
