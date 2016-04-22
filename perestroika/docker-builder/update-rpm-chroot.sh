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

if [ ! -f "${BIN}/mockbuild/centos${DIST_VERSION}.conf" ] ; then
  echo "Unknown dist version: ${DIST_VERSION}"
  exit 1
fi

source ${BIN}/mockbuild/centos${DIST_VERSION}.conf
CONFIG_CONTENT_BASE64=$(echo "${CONFIG_CONTENT}" | base64 -w0)
docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}/cache:/var/cache/mock ${CONTAINERNAME} \
    bash -c "
       mkdir -p /var/cache/mock/configs
       cp /etc/mock/logging.ini /var/cache/mock/configs/
       rm -rf /etc/mock
       ln -s /var/cache/mock/configs /etc/mock
       rm -rf /var/cache/mock/epel-${DIST_VERSION}-x86_64/yum_cache
       rm -f /etc/mock/centos-${DIST_VERSION}-x86_64.cfg
       echo \"${CONFIG_CONTENT_BASE64}\" \
           | base64 -d > /etc/mock/centos-${DIST_VERSION}-x86_64.cfg
       echo 'Current config file:'
       cat /etc/mock/centos-${DIST_VERSION}-x86_64.cfg
       su - abuild -c 'mock -r centos-${DIST_VERSION}-x86_64 -v --update'"
