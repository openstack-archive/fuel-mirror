#!/bin/bash -ex

usage() {
cat <<EOF
Usage: `basename $0` [options]

If NO parameters specified, this script will:
- search for sources in the local directory
- put built packages to ./buildresult
- use the preconfigured upstream mirror (http://mirror.yandex.ru/ubuntu)

Mandatory arguments to long options are mandatory for short options too.
    -h, --help                  display this help and exit
    -b, --build-target          distname (currently "trusty" and "7" are supported)
    -s, --source                sources directory
    -u, --upstream-repo         upstream mirror (default is mirror.yandex.ru/ubuntu)
    -r, --ext-repos             additional mirrors
    -o, --output-dir            output directory

Please use the following syntax to add additional repositories:
rpm:
  "name1,http://url/to/repo1|name2,http://url/to/repo2"
deb:
  "http://url/to/repo1 distro component1 component2|http://url/to/repo2 distro component3 component4"

IMPORTANT:
Sources should be prepared by the maintainer before the build:
rpm:
 - srpm file:
   ./python-amqp-1.4.5-2.mira1.src.rpm
 - file tree with .spec file and source tarball:
   ./python-pbr-0.10.0.tar.gz
   ./some-patch.patch
   ./python-pbr.spec
deb:
 - packed sources (.dsc, .*z , .diff files):
   ./websocket-client_0.12.0-ubuntu1.debian.tar.gz
   ./websocket-client_0.12.0-ubuntu1.dsc
   ./websocket-client_0.12.0.orig.tar.gz
 - file tree with pristine source tarball in the root of tree and debian folder inside some parent folder:
   ./python-pbr/debian/*
   ./python-pbr_0.10.0.orig.tar.gz

EOF
}

usage_short() {
    echo Usage: `basename $0` [options]
    echo
    echo -e Try \``basename $0` --help\' for more options.
}

die() { echo "$@" 1>&2 ; exit 1; }

OPTS=`getopt -o b:s:e:o:u:h -l build-target:,source:,ext-repos:,output-dir:,upstream-repo:,help -- "$@"`
if [ $? != 0 ]; then
    usage_short
    exit 1
fi

eval set -- "$OPTS"

WORKING_DIR=${0%/*}

while true ; do
    case "$1" in
        -h| --help ) usage ; exit 0;;
        -b | --build-target ) BUILD_TARGET="$2"; shift; shift;;
        -s | --source ) BUILD_SOURCE="$2"; shift; shift;;
        -e | --ext-repos ) EXTRAREPO="$2"; export EXTRAREPO; shift; shift;;
        -o | --output-dir ) OUTPUT_DIR="$2"; shift; shift;;
        -u | --upstream-repo ) UPSTREAM_MIRROR="$2"; export UPSTREAM_MIRROR; shift; shift;;
        --                ) shift; break;;
        *                 ) break;;
    esac
done

if [[ ${BUILD_SOURCE} = "" ]]; then
  BUILD_SOURCE=`pwd`
fi

build_docker_image() {
    docker build -t mockbuild ${WORKING_DIR}/docker-builder/mockbuild/
    docker build -t sbuild ${WORKING_DIR}/docker-builder/sbuild/
}

create_buildroot() {
  if [[ ${BUILD_TARGET} = "7" ]]; then ${WORKING_DIR}/docker-builder/create-rpm-chroot.sh; fi
  if [[ ${BUILD_TARGET} = "trusty" ]]; then ${WORKING_DIR}/docker-builder/create-deb-chroot.sh; fi
}

update_buildroot() {
  if [[ ${BUILD_TARGET} = "7" ]]; then ${WORKING_DIR}/docker-builder/update-rpm-chroot.sh; fi
  if [[ ${BUILD_TARGET} = "trusty" ]]; then ${WORKING_DIR}/docker-builder/update-deb-chroot.sh; fi
}

main () {
case "$BUILD_TARGET" in
        trusty)
          if [[ "$(docker images -q sbuild 2> /dev/null)" == "" ]]; then
            build_docker_image
            create_buildroot
          else
            if [[ ! -d /var/cache/docker-builder/sbuild/${BUILD_TARGET}-amd64 ]]; then
              create_buildroot
            else
              update_buildroot
            fi
          fi
          cd ${BUILD_SOURCE} && DIST=${BUILD_TARGET} ${WORKING_DIR}/docker-builder/build-deb-package.sh
          if [[ ${OUTPUT_DIR} != "" ]]; then
            mkdir -p ${OUTPUT_DIR}
            mv buildresult/* ${OUTPUT_DIR}
            rm -rf buildresult
          fi
        ;;
        7)
          if [[ "$(docker images -q mockbuild 2> /dev/null)" == "" ]]; then
            build_docker_image
            create_buildroot
          else
            if [[ ! -d /var/cache/docker-builder/mock/cache/*-${BUILD_TARGET}-x86_64 ]]; then
              create_buildroot
            else
              update_buildroot
            fi
          fi
          cd ${BUILD_SOURCE} && pwd && DIST=${BUILD_TARGET} ${WORKING_DIR}/docker-builder/build-rpm-package.sh
          if [[ ${OUTPUT_DIR} != "" ]]; then
            mkdir -p ${OUTPUT_DIR}
            mv build/* ${OUTPUT_DIR}
            rm -rf build
          fi
        ;;
        *) die "Unknown build target specified. Currently "trusty" and "7" are supported"
esac
}

main "${@}"
