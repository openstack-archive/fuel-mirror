#!/bin/bash

set -o xtrace
set -o errexit
set -o pipefail

SOURCE_DIR=$1

if [ -z "${SOURCE_DIR}" ]; then
  echo "Please provide path to sources"
  exit 1;
fi

if [ ! -d "${SOURCE_DIR}" ]; then
  echo "No such directory: ${SOURCE_DIR}"
  exit 1;
fi

# root path to perestroika repo
BINDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )

BUILD_DIR="${SOURCE_DIR}/build_dir"
# clean build dir
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

SPEC_DIR="${SOURCE_DIR}/specs"
SPEC_FILE=$(find "${SPEC_DIR}" -name "*.spec")

if [ -z "${SPEC_FILE}" ]; then
  echo "No SPEC file found in directory: ${SPEC_DIR}"
  exit 1;
fi

# TAR_NAME=${SPEC_FILE##*/}.tar.gz
# sed -i "s|Source0:.*$|Source0: ${TAR_NAME}|" "${SPEC_FILE}"

# cd "${SOURCE_DIR}"
# git archive --format=tar.gz --worktree-attributes HEAD --output="${BUILD_DIR}/${TAR_NAME}"
# cp -v "${SPEC_FILE}" "${BUILD_DIR}"


export EXTRAREPO="repo1,http://perestroika-repo-tst.infra.mirantis.net/mos-repos//centos/mos8.0-centos7-fuel/os/x86_64"

cd "${BUILD_DIR}"
"${BINDIR}"/docker-builder/build-rpm-package.sh
