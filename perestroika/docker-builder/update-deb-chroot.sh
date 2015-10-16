#!/bin/bash

set -ex

BIN="${0%/*}"

source "${BIN}/config"

CONTAINERNAME=sbuild:latest
CACHEPATH=/var/cache/docker-builder/sbuild

# Use trusty distro by default
[ -z "${DIST}" ] && DIST=trusty

if [ "${DIST}" != "precise" ] && [ "${DIST}" != "trusty" ]; then
  echo "Unknown dist version: ${DIST}"
  exit 1
fi

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}:/srv/images ${CONTAINERNAME} \
    bash -c "sbuild-update -udcar ${DIST}"
