#!/bin/bash

#set -ex

#Input properties
PACKAGENAME="ironic"
SRC_PROJECT="openstack/ironic"
REPO="8.0"

source ./properties.sh
source ./check-package-functions.sh

UBUNTU_REPO="${PACKAGES_REPO_HOST}/ubuntu/${REPO}"
UBUNTU_TEMP_DIR="${TEMP_DIR}/ubuntu"
if [ -d "${UBUNTU_TEMP_DIR}" ]; then
    rm -rf "${UBUNTU_TEMP_DIR}"
fi

mkdir "${UBUNTU_TEMP_DIR}"

#----------------------------------------------------------------
# Step 1 : Get binary repo index files
#----------------------------------------------------------------
UBUNTU_RELEASE_DOWNLOAD_PATH="${UBUNTU_REPO}/dists/mos8.0/Release"
UBUNTU_RELEASE_FILE="${UBUNTU_TEMP_DIR}/Release"

wget -O $UBUNTU_RELEASE_FILE $UBUNTU_RELEASE_DOWNLOAD_PATH

ARCHS=$(awk -F ':' '/Architectures/ {print $2}' $UBUNTU_RELEASE_FILE)

for arch in $ARCHS; do
    UBUNTU_PACKAGE_DOWNLOAD_PATH="${UBUNTU_REPO}/dists/mos8.0/main/binary-${arch}/Packages"
    UBUNTU_PACKAGE_FILE="${UBUNTU_TEMP_DIR}/Packages-$arch"

    wget -O $UBUNTU_PACKAGE_FILE $UBUNTU_PACKAGE_DOWNLOAD_PATH

done
# FIXME : Check for all Packages files if paths are different

#---------------------------------------------------------------------
# Step 2 : Get timestamp from Release file
#---------------------------------------------------------------------
DATE_STAMP=$(grep ^Date: ${UBUNTU_RELEASE_FILE}| awk -F ':' '{print $2":"$3":"$4}' | awk -F ' ' '{print $2, $3, $4, $5, $6}' | xargs -0 date "+%Y-%m-%d %H:%M:%S" -d)
TIME_BEFORE=$(date "+%Y-%m-%d %H:%M:00" --date "${DATE_STAMP} 1 minutes")

#---------------------------------------------------------------------
# Step 3 : Get gerrit details for the project
#---------------------------------------------------------------------
GERRIT_COMMIT_INFO_FILE_PATH="${UBUNTU_TEMP_DIR}/commit_info.txt"
get_gerrit_properties

#--------------------------------------------------------------------
# Step 4 : Clone the repository and get the required state
#--------------------------------------------------------------------
PROJECT_SRC_DIR="${SRC_DIR}/${GERRIT_PROJECT_NAME}"

if [ -d "$PROJECT_SRC_DIR" ]; then
    rm -rf $PROJECT_SRC_DIR
fi

get_gerrit_patchset

#--------------------------------------------------------------------
# Step 5 : Calculate release from sources
#--------------------------------------------------------------------

#FIXME: if not Fuel
get_deb_package_release



#--------------------------------------------------------------------
# Step 6 : Get package name, version and release from index files
#--------------------------------------------------------------------

SOURCE_LINES=$(grep -onP "Source:\s*${PACKAGENAME}" $UBUNTU_PACKAGE_FILE | awk -F ':' '{print $1}')

for source_line in ${SOURCE_LINES[@]}; do
    package_line=$((source_line-1))
    version_line=$((source_line+1))

    package=$(awk -v search_line=$package_line 'NR==search_line && /Package:/ {print $2}' $UBUNTU_PACKAGE_FILE)
    version=$(awk -v search_line=$version_line 'NR==search_line && /Version:/ {print $2}' $UBUNTU_PACKAGE_FILE)

    release_regex="mos\K(\d+)"
    bin_release=$(echo $version | grep -oP $release_regex)

    #--------------------------------------------------------------------
    # Step 7 : Check if release is the same
    #--------------------------------------------------------------------
    if [ "$bin_release" = "$GERRIT_MOS_RELEASE" ]; then
        echo "${package} - ${version} - CONSISTENT"
    else
        echo "${package} - ${version} - INCOSISTENT"
    fi
done




