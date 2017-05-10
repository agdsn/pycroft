#!/bin/bash
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

# registry is needed in any way
if [[ -z $REGISTRY ]]; then
    echo "REGISTRY must be provided"
    exit 1
fi

register_cert() {
    # TODO: check it will be applied without restart
    if [[ -z $REGISTRY_CERT_BASE64 ]]; then
        echo "REGISTRY_CERT_BASE64 not set. Skipping."
        return
    fi

    local tmp_cert_file=$(mktemp)
    <<<$REGISTRY_CERT_BASE64 base64 -d > $tmp_cert_file

    local cert_file=/etc/docker/certs.d/$(basename $REGISTRY)/ca.crt

    if [[ -f $cert_file ]]; then
        echo "WARNING: File Exists. Overwriting."
    fi

    if [[ $EUID != 0 ]]; then
        echo "Insufficient privileges to install certificate, leaving as is"
        return
    fi

    local cert_dir=$(dirname $cert_file)
    if [[ ! -d $cert_dir ]]; then
        echo "Creating $cert_dir"
        mkdir -p $cert_dir
    fi
    echo "Writing cert to $cert_file"
    <<<$REGISTRY_CERT_BASE64 base64 -d > $cert_file
}

login() {
    if [[ -z $REGISTRY_USER || -z $REGISTRY_PASSWORD ]]; then
        echo "REGISTRY_USER and REGISTRY_PASSWORD must be provided"
        exit 1
    fi
    if [[ -z $REGISTRY ]]; then
        echo -n "LOGIN: as $REGISTRY_USER to the dockerhub (no REGISTRY given). "
    else
        echo -n "LOGIN: as $REGISTRY_USER to $REGISTRY. "
    fi
    docker login -u $REGISTRY_USER -p $REGISTRY_PASSWORD $REGISTRY
}

logout_() {
    echo -n "LOGOUT: " && docker logout $REGISTRY
}

_build_complete_tag() {  # registry, image, [tag:latest]
    local host=$(basename $1)
    local image=$2
    if [[ -n $3 ]]; then
        local tag=$3
    else
        local tag="latest"
    fi
    echo $host/$image:$tag
}

_tag_and_push() {  # image, tag
    local image=$1
    local tag=$2
    local ref=$(_build_complete_tag $REGISTRY $image $tag)

    echo "Tagging and pushing $ref ..."
    if [[ $tag != latest ]]; then
        # retag as desired
        docker tag $image:latest $ref
    fi
    docker push $ref
    echo "...done."
}

push() {
    if [[ -z $DOCKER_IMAGE_NAME ]]; then
        local image=pycroft
    else
        local image=$DOCKER_IMAGE_NAME
    fi

    echo "PUSH: $image:latest"

    _tag_and_push $image develop
    if [[ $TRAVIS_BRANCH == "master" ]]; then
        _tag_and_push $image latest
    fi
    if [[ -n $TRAVIS_TAG ]]; then
        _tag_and_push $image $TRAVIS_TAG
    fi
}

all() {
    register_cert && login && push && logout_
}

if [[ $1 =~ ^(register_cert|login|push|all)$ ]]; then
    "$@"
else
    echo "Invalid subcommand $1" >&2
    echo "Available subcommands: register_cert,login,push,all"
    exit 1
fi
