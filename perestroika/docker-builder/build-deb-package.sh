#!/bin/bash -ex
. $(dirname $(readlink -f $0))/config
CONTAINERNAME=sbuild:latest
CACHEPATH=/var/cache/docker-builder/sbuild
[ -z "$DIST" ] && DIST=trusty

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
    bash -c "( sed -i '/debian\/rules/d' /usr/bin/sbuild

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
