#!/bin/bash -ex
. $(dirname $(readlink -f $0))/config
CONTAINERNAME=sbuild:latest
CACHEPATH=/var/cache/docker-builder/sbuild

BIN=$(dirname `readlink -e $0`)

[ -z "$DIST" ] && DIST=trusty

if [ ! -f "${BIN}/sbuild/${DIST}-amd64-sbuild" ] ; then
    echo "Unknown dist version: ${DIST}"
    exit 1
fi

DIST_CONFIG="$(cat ${BIN}/sbuild/${DIST}-amd64-sbuild)"

# Add extra repositories
if [ -n "$EXTRAREPO" ] ; then
    EXTRACMD=""
    OLDIFS="$IFS"
    IFS='|'
    for repo in $EXTRAREPO; do
      IFS="$OLDIFS"
      EXTRACMD="${EXTRACMD} --chroot-setup-commands=\"apt-add-repo deb $repo\" "
      IFS='|'
    done
    IFS="$OLDIFS"
fi

dscfile=$(find . -maxdepth 1 -name \*.dsc | head -1)
debianfolder=$(find . -wholename "*debian/changelog*" | head -1 | sed 's|^./||; s|debian/changelog||')

if [ -n "$dscfile" ]; then
    SOURCEDEST=$dscfile
    SOURCEDEST=`basename $SOURCEDEST`
elif [ -n "$debianfolder" ] ; then
    SOURCEDEST=$debianfolder
fi

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}:/srv/images:ro \
    -v $(pwd):/srv/source ${CONTAINERNAME} \
    bash -c "rm -rf /etc/schroot/chroot.d
             mkdir -p /srv/images/chroot.d
             ln -s /srv/images/chroot.d /etc/schroot/chroot.d
             [ ! -f /etc/schroot/chroot.d/${DIST}-amd64-sbuild ] \
                 && echo \"$DIST_CONFIG\" > /etc/schroot/chroot.d/${DIST}-amd64-sbuild
             ( sed -i '/debian\/rules/d' /usr/bin/sbuild
             DEB_BUILD_OPTIONS=nocheck /usr/bin/sbuild -d ${DIST} --nolog \
                 --source --force-orig-source \
                 $EXTRACMD \
                 --chroot-setup-commands=\"apt-get update\" \
                 --chroot-setup-commands=\"apt-get upgrade -f -y --force-yes\" \
                 /srv/source/${SOURCEDEST} 2>&1
             echo \$? > /srv/build/exitstatus.sbuild ) \
                 | tee /srv/build/buildlog.sbuild
             rm -rf /srv/source/buildresult
             mv /srv/build /srv/source/buildresult
             chown -R `id -u`:`id -g` /srv/source"
