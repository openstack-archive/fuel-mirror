#!/bin/bash -ex
. $(dirname $(readlink -f $0))/config
CONTAINERNAME=mockbuild:latest
CACHEPATH=/var/cache/docker-builder/mock
DIST_VERSION=`echo $DIST | sed 's|centos||'`
[ -z "${DIST_VERSION}" ] && DIST_VERSION=7

EXTRACMD=":"
if [ -n "$EXTRAREPO" ] ; then
   EXTRACMD="sed -i"
   OLDIFS="$IFS"
   IFS='|'
   for repo in $EXTRAREPO ; do
     IFS="$OLDIFS"
     reponame=${repo%%,*}
     repourl=${repo##*,}
     EXTRACMD="$EXTRACMD -e \"$ i[${reponame}]\nname=${reponame}\nbaseurl=${repourl}\ngpgcheck=0\nenabled=1\nskip_if_unavailable=1\""
     IFS='|'
   done
   IFS="$OLDIFS"
   EXTRACMD="$EXTRACMD /etc/mock/centos-${DIST_VERSION}-x86_64.cfg"
fi

docker run ${DNSPARAM} --privileged --rm -v ${CACHEPATH}:/srv/mock:ro \
    -v $(pwd):/home/abuild/rpmbuild ${CONTAINERNAME} \
    bash -x -c "mkdir -p /srv/tmpfs/cache
        mount -t tmpfs overlay /srv/tmpfs/cache
        mount -t aufs -o br=/srv/tmpfs/cache/:/srv/mock/cache none /var/cache/mock/
        $EXTRACMD
        su - abuild -c 'mock -r centos-${DIST_VERSION}-x86_64 --verbose --update'
        chown -R abuild.mock /home/abuild
        [[ \$(ls /home/abuild/rpmbuild/*.src.rpm | wc -l) -eq 0 ]] \
            && su - abuild -c 'mock -r centos-${DIST_VERSION}-x86_64 --no-clean --no-cleanup-after --buildsrpm --verbose \
               --sources=/home/abuild/rpmbuild --resultdir=/home/abuild/rpmbuild --buildsrpm \
               --spec=\$(ls /home/abuild/rpmbuild/*.spec)'
        rm -rf /home/abuild/rpmbuild/build
        su - abuild -c 'mock -r centos-${DIST_VERSION}-x86_64 --no-clean --no-cleanup-after --verbose \
             --resultdir=/home/abuild/rpmbuild/build \$(ls /home/abuild/rpmbuild/*.src.rpm)'
        echo \$? > /home/abuild/rpmbuild/build/exitstatus.mock
        umount -f /var/cache/mock /srv/tmpfs/cache
        rm -rf /srv/tmpfs
        rm -f /home/abuild/rpmbuild/\*.src.rpm /home/abuild/rpmbuild/{build,root,state}.log
        chown -R `id -u`:`id -g` /home/abuild"
