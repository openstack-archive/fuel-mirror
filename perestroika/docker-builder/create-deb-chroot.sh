#!/bin/bash
#
# Prepare chroot (must exist before starting any builds) environment
# with `sbuild-createchroot` which prepares everything for building DEBs
#
# Usage:  DIST=trusty  ./create-deb-chroot.sh     # for Trusty
#         DIST=precise ./create-deb-chroot.sh     # for Precise

set -ex

BIN=$(dirname `readlink -e $0`)

source "${BIN}/config"
exit 1
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
MIRROR=$(echo "$DIST_REPOS" | head -1 | awk '{print $2}')

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}:/srv/images ${CONTAINERNAME} \
    bash -c "rm -rf /etc/schroot/chroot.d
             mkdir -p /srv/images/chroot.d
             ln -s /srv/images/chroot.d /etc/schroot/chroot.d
             rm -f /etc/schroot/chroot.d/${DIST}-amd64-sbuild*
             rm -rf /srv/images/${DIST}-amd64
             sbuild-createchroot ${DIST} /srv/images/${DIST}-amd64 ${MIRROR}
             mv /etc/schroot/chroot.d/${DIST}-amd64-sbuild* /etc/schroot/chroot.d/${DIST}-amd64-sbuild
             echo 'union-type=aufs' >> /etc/schroot/chroot.d/${DIST}-amd64-sbuild
             echo \"$DIST_REPOS\" > /srv/images/${DIST}-amd64/etc/apt/sources.list
             sbuild-update -udcar ${DIST}
             echo '#!/bin/bash' > /srv/images/${DIST}-amd64/usr/bin/apt-add-repo
             echo 'echo \$* >> /etc/apt/sources.list' >> /srv/images/${DIST}-amd64/usr/bin/apt-add-repo
             chmod +x /srv/images/${DIST}-amd64/usr/bin/apt-add-repo"
