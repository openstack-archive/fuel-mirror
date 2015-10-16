#!/bin/bash
#
# Prepare chroot (must exist before starting any builds) environment
# with `mock --init` which installs all packages (@buildsys-build)
# required for building RPMs
#
# Usage:  DIST=6 ./create-rpm-chroot.sh     # for CentOS 6
#         DIST=7 ./create-rpm-chroot.sh     # for CentOS 7

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
    bash -c "chown -R abuild:mock /var/cache/mock
             chmod g+s /var/cache/mock
             su - abuild -c 'mock -r centos-${DIST_VERSION}-x86_64 -v --init'"
