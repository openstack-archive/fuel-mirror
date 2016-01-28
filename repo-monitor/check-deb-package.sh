#!/bin/bash

set -ex

#Input properties
PACKAGE_NAME="ironic-api"
REPO="8.0"

source ./properties.sh
source ./check-package-functions.sh

UBUNTU_REPO="${PACKAGES_REPO_HOST}/ubuntu/${REPO}"

if [ -d "$TEMP_DIR" ]; then
    rm -rf $TEMP_DIR
fi

mkdir $TEMP_DIR

#----------------------------------------------------------------
# Step 1 : Get binary repo index files
#----------------------------------------------------------------
UBUNTU_RELEASE_DOWNLOAD_PATH="${UBUNTU_REPO}/dists/mos8.0/Release"
UBUNTU_RELEASE_FILE="${TEMP_DIR}/Release"

wget -O $UBUNTU_RELEASE_FILE $UBUNTU_RELEASE_DOWNLOAD_PATH

ARCHS=$(awk -F ':' '/Architectures/ {print $2}' $UBUNTU_RELEASE_FILE)

for arch in $ARCHS; do
    UBUNTU_PACKAGE_DOWNLOAD_PATH="${UBUNTU_REPO}/dists/mos8.0/main/binary-${arch}/Packages"
    UBUNTU_PACKAGE_FILE="${TEMP_DIR}/Packages-$arch"

    wget -O $UBUNTU_PACKAGE_FILE $UBUNTU_PACKAGE_DOWNLOAD_PATH

done
# FIXME : Check for all Packages files if paths are different

#--------------------------------------------------------------------
# Step 2 : Get package version and release from index files
#--------------------------------------------------------------------
PACKAGE_START_LINE=$(grep -n "Package:\s*${PACKAGE_NAME}" $UBUNTU_PACKAGE_FILE | awk -F ':' '{print $1}')
PACKAGE_END_LINE=$((PACKAGE_START_LINE+15)) #FIXME: magic number
PACKAGE_VERSION=$(awk -v from=$PACKAGE_START_LINE -v to=$PACKAGE_END_LINE 'NR>=from && NR<=to && /Version:/ {print $2}' $UBUNTU_PACKAGE_FILE)

MOS_RELEASE_REGEX="mos\K(\d+)"
BIN_MOS_RELEASE=$(echo $PACKAGE_VERSION | grep -oP $MOS_RELEASE_REGEX)

# FIXME : Check all the packages from the list. Or get the list form repo
#PACKAGES_LIST=$(grep $PACKAGE_NAME $PROJECT_INFO_FILE |awk '{print $1}')

#---------------------------------------------------------------------
# Step 3 : Get timestamp from Release file
#---------------------------------------------------------------------
DATE_STAMP=$(grep ^Date: ${UBUNTU_RELEASE_FILE}| awk -F ':' '{print $2":"$3":"$4}' | awk -F ' ' '{print $2, $3, $4, $5, $6}' | xargs -0 date "+%Y-%m-%d %H:%M:%S" -d)
TIME_BEFORE=$(date "+%Y-%m-%d %H:%M:00" --date "${DATE_STAMP} 1 minutes")

#---------------------------------------------------------------------
# Step 4 : Get gerrit details for the project
#---------------------------------------------------------------------
get_gerrit_properties

#--------------------------------------------------------------------
# Step 5 : Clone the repository and get the required state
#--------------------------------------------------------------------
PROJECT_SRC_DIR="${SRC_DIR}/${GERRIT_PROJECT_NAME}"

if [ -d "$PROJECT_SRC_DIR" ]; then
    rm -rf $PROJECT_SRC_DIR
fi

get_gerrit_patchset

#--------------------------------------------------------------------
# Step 6 : Calculate release from sources
#--------------------------------------------------------------------

#FIXME: if not Fuel
get_deb_package_release

#--------------------------------------------------------------------
# Step 7 : Check if release is the same
#--------------------------------------------------------------------
if [ "$BIN_MOS_RELEASE" = "$GERRIT_MOS_RELEASE" ]; then
    echo "CONSISTENT!"
else
    echo "INCOSISTENT"
fi
