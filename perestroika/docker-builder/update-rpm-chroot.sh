#!/bin/bash

set -ex

BIN="${0%/*}"

source "${BIN}/config"

CONTAINERNAME=mockbuild:latest
CACHEPATH=/var/cache/docker-builder/mock

# check DIST=centos6 which can be passed from upstream job or defined in env
DIST_VERSION=${DIST/centos/}
# by default we init env for CentOS 7
[ -z "${DIST_VERSION}" ] && DIST_VERSION=7

if [ "${DIST_VERSION}" != 6 ] && [ "${DIST_VERSION}" != 7 ]; then
  echo "Unknown dist version: ${DIST_VERSION}"
  exit 1
fi

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}/cache:/var/cache/mock ${CONTAINERNAME} \
    bash -c "su - abuild -c 'mock -r centos-${DIST_VERSION}-x86_64 -v --update'"
