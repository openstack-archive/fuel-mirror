#!/bin/bash

set -ex

#Input properties
PACKAGE_NAME="openstack-cinder"
REPO="mos8.0-centos7-fuel"

source ./properties.sh
source ./check-package-functions.sh

CENTOS_REPO="${PACKAGES_REPO_HOST}/centos/${REPO}"

if [ -d "$TEMP_DIR" ]; then
    rm -rf $TEMP_DIR
fi

mkdir $TEMP_DIR

#----------------------------------------------------------------
# Step 1 : Get binary repo index files
#----------------------------------------------------------------
REPOMD_DOWNLOAD_PATH="http://${CENTOS_REPO}/os/x86_64/repodata/repomd.xml"

wget -P $TEMP_DIR $REPOMD_DOWNLOAD_PATH
wget -A '-primary.sqlite.bz2' --no-parent -r -l 1 -nd -P $TEMP_DIR "http://${CENTOS_REPO}/os/x86_64/repodata/"

XML_BZNAME_REGEX="repodata/\K(\w*-primary.sqlite.bz2)"
REPOMD_BZ_FILE_NAME=$(grep -oP "${XML_BZNAME_REGEX}"  "${TEMP_DIR}/repomd.xml")
REAL_BZ_FILE_NAME=$(ls ${TEMP_DIR} | grep .sqlite.bz)

if [ "$REPOMD_BZ_FILE_NAME" != "$REAL_BZ_FILE_NAME" ]; then
    echo "Repo index is incosistent"
    exit 1;
fi

bzip2 -df  "${TEMP_DIR}/${REAL_BZ_FILE_NAME}"

#--------------------------------------------------------------------
# Step 2 : Get package version and release from index files
#--------------------------------------------------------------------
SQLITE_FILE=$(ls ${TEMP_DIR} | grep .sqlite)
SQLITE_FIELDS="name,version,release"
SQLITE_REQUEST="select ${SQLITE_FIELDS} from packages where name = '${PACKAGE_NAME}';"
PACKAGE_INFO=$(sqlite3 "${TEMP_DIR}/${SQLITE_FILE}" "${SQLITE_REQUEST}")

MOS_RELEASE_REGEX="mos\K(\d+)"
BIN_MOS_RELEASE=$(echo $PACKAGE_INFO | awk -F '|' '{print $3}' | grep -oP $MOS_RELEASE_REGEX)

# FIXME : Check all the packages from the list. Or get the list form repo
#PACKAGES_LIST=$(grep ${PACKAGE_NAME} ./projects.txt |awk '{print $1}')

#---------------------------------------------------------------------
# Step 3 : Get timestamp from repomd file
#---------------------------------------------------------------------
REPOMD_START_LINE=$(grep -onP "${XML_BZNAME_REGEX}"  "${TEMP_DIR}/repomd.xml" | awk -F ':' '{print $1}')
TIMESTAMP_TAG_REGEXP="<timestamp>\K(\d+)"
REPOMD_UPDATE_UTIME=$(tail -n +${REPOMD_START_LINE} ${TEMP_DIR}/repomd.xml | grep -oP -m 1 "$TIMESTAMP_TAG_REGEXP")
TIME_BEFORE=$(date "+%Y-%m-%d %H:%M:00" --date @${REPOMD_UPDATE_UTIME})

#---------------------------------------------------------------------
# Step 4 : Get gerrit details for the project
#---------------------------------------------------------------------
get_gerrit_properties

#--------------------------------------------------------------------
# Step 5 : Clone the repository and get the required state
#--------------------------------------------------------------------
PROJECT_SRC_DIR="${SRC_DIR}/${GERRIT_PROJECT_NAME}"

if [ -d "$PROJECT_SRC_DIR" ]; then
    echo "Deleting $PROJECT_SRC_DIR"
    rm -rf $PROJECT_SRC_DIR
fi

get_gerrit_patchset

#--------------------------------------------------------------------
# Step 6 : Calculate release from sources
#--------------------------------------------------------------------
#FIXME: if not Fuel
#TAG_REGEX="\d+\.\d+\.\d+"
#RELEASE_TAG=$(echo $PACKAGE_INFO | awk -F '|' '{print $2}' | grep -oP $TAG_REGEX)
#GERRIT_MOS_RELEASE=$(git -C ${PROJECT_SRC_DIR} rev-list --no-merges ${RELEASE_TAG}..origin/${GERRIT_MERGEDTO} | wc -l)
get_rpm_package_release

if [ "$BIN_MOS_RELEASE" -eq "$GERRIT_MOS_RELEASE" ]; then
    echo "CONSISTENT!"
else
    echo "INCOSISTENT"
fi
