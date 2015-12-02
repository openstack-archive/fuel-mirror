#!/bin/bash

set -ex

BIN=$(dirname `readlink -e $0`)

source "${BIN}/config"

CONTAINERNAME=sbuild:latest
CACHEPATH=/var/cache/docker-builder/sbuild

# Use trusty distro by default
[ -z "${DIST}" ] && DIST=trusty

if [ ! -f "${BIN}/sbuild/${DIST}-amd64-sbuild" ] ; then
    echo "Unknown dist version: ${DIST}"
    exit 1
fi

DIST_CONFIG="$(cat ${BIN}/sbuild/${DIST}-amd64-sbuild)"
DIST_REPOS="$(cat ${BIN}/sbuild/${DIST}-amd64-aptsources)"

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}:/srv/images ${CONTAINERNAME} \
    bash -c "rm -rf /etc/schroot/chroot.d
             mkdir -p /srv/images/chroot.d
             ln -s /srv/images/chroot.d /etc/schroot/chroot.d
             [ ! -f /etc/schroot/chroot.d/${DIST}-amd64-sbuild ] \
                 && echo \"$DIST_CONFIG\" > /etc/schroot/chroot.d/${DIST}-amd64-sbuild
             echo \"$DIST_REPOS\" > /srv/images/${DIST}-amd64/etc/apt/sources.list
             sbuild-update -udcar ${DIST}"
