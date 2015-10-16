#!/bin/bash
#
# Prepare chroot (must exist before starting any builds) environment
# with `sbuild-createchroot` which prepares everything for building DEBs
#
# Usage:  DIST=trusty  ./create-deb-chroot.sh     # for Trusty
#         DIST=precise ./create-deb-chroot.sh     # for Precise
#         UPSTREAM_MIRROR=http://ua.archive.ubuntu.com/ubuntu/ ./create-deb-chroot.sh

set -ex

BIN="${0%/*}"

source "${BIN}/config"

CONTAINERNAME=sbuild:latest
CACHEPATH=/var/cache/docker-builder/sbuild
# define upstream Ubuntu mirror
MIRROR=${UPSTREAM_MIRROR:-http://mirror.yandex.ru/ubuntu}
# Use trusty distro by default
[ -z "${DIST}" ] && DIST=trusty

if [ "${DIST}" != "precise" ] && [ "${DIST}" != "trusty" ]; then
  echo "Unknown dist version: ${DIST}"
  exit 1
fi

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}:/srv/images ${CONTAINERNAME} \
    bash -c "rm -f /etc/schroot/chroot.d/*
             sbuild-createchroot ${DIST} /srv/images/${DIST}-amd64 ${MIRROR}
             echo deb ${MIRROR} ${DIST} main universe multiverse restricted > /srv/images/${DIST}-amd64/etc/apt/sources.list
             echo deb ${MIRROR} ${DIST}-updates main universe multiverse restricted >> /srv/images/${DIST}-amd64/etc/apt/sources.list
             sbuild-update -udcar ${DIST}
             echo '#!/bin/bash' > /srv/images/${DIST}-amd64/usr/bin/apt-add-repo
             echo 'echo \$* >> /etc/apt/sources.list' >> /srv/images/${DIST}-amd64/usr/bin/apt-add-repo
             chmod +x /srv/images/${DIST}-amd64/usr/bin/apt-add-repo"
