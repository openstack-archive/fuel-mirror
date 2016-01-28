#!/bin/bash

#set -ex

#Input properties
PACKAGENAME="openstack-cinder"
SRC_PROJECT="openstack/cinder"
REPO="mos8.0-centos7-fuel"

source ./properties.sh
source ./check-package-functions.sh

CENTOS_REPO="${PACKAGES_REPO_HOST}/centos/${REPO}"
CENTOS_TEMP_DIR="${TEMP_DIR}/centos"

if [ -d "$CENTOS_TEMP_DIR" ]; then
    rm -rf $CENTOS_TEMP_DIR
fi

mkdir $CENTOS_TEMP_DIR

#----------------------------------------------------------------
# Step 1 : Get binary repo index files
#----------------------------------------------------------------
REPOMD_DOWNLOAD_PATH="http://${CENTOS_REPO}/os/x86_64/repodata/repomd.xml"

wget -P $CENTOS_TEMP_DIR $REPOMD_DOWNLOAD_PATH
wget -A '-primary.sqlite.bz2' --no-parent -r -l 1 -nd -P $CENTOS_TEMP_DIR "http://${CENTOS_REPO}/os/x86_64/repodata/"

XML_BZNAME_REGEX="repodata/\K(\w*-primary.sqlite.bz2)"
REPOMD_BZ_FILE_NAME=$(grep -oP "${XML_BZNAME_REGEX}"  "${CENTOS_TEMP_DIR}/repomd.xml")
REAL_BZ_FILE_NAME=$(ls ${CENTOS_TEMP_DIR} | grep .sqlite.bz)

if [ "$REPOMD_BZ_FILE_NAME" != "$REAL_BZ_FILE_NAME" ]; then
    echo "Repo index is incosistent"
    exit 1;
fi

bzip2 -df  "${CENTOS_TEMP_DIR}/${REAL_BZ_FILE_NAME}"

#---------------------------------------------------------------------
# Step 2 : Get timestamp from repomd file
#---------------------------------------------------------------------
REPOMD_XML="${CENTOS_TEMP_DIR}/repomd.xml"
REPOMD_START_LINE=$(grep -onP "${XML_BZNAME_REGEX}" $REPOMD_XML  | awk -F ':' '{print $1}')
TIMESTAMP_TAG_REGEXP="<timestamp>\K(\d+)"
REPOMD_UPDATE_UTIME=$(tail -n +${REPOMD_START_LINE} $REPOMD_XML | grep -oP -m 1 "$TIMESTAMP_TAG_REGEXP")
TIME_BEFORE=$(date "+%Y-%m-%d %H:%M:00" --date @${REPOMD_UPDATE_UTIME})

#---------------------------------------------------------------------
# Step 3 : Get gerrit details for the project
#---------------------------------------------------------------------
GERRIT_COMMIT_INFO_FILE_PATH="${CENTOS_TEMP_DIR}/commit_info.txt"
get_gerrit_properties

#--------------------------------------------------------------------
# Step 4 : Clone the repository and get the required state
#--------------------------------------------------------------------
PROJECT_SRC_DIR="${SRC_DIR}/${GERRIT_PROJECT_NAME}"

if [ -d "$PROJECT_SRC_DIR" ]; then
    echo "Deleting $PROJECT_SRC_DIR"
    rm -rf $PROJECT_SRC_DIR
fi

get_gerrit_patchset

#--------------------------------------------------------------------
# Step 5 : Calculate release from sources
#--------------------------------------------------------------------
#FIXME: if not Fuel

get_rpm_package_release

#--------------------------------------------------------------------
# Step 2 : Get package version and release from index files
#--------------------------------------------------------------------
SQLITE_FILE=$(ls ${CENTOS_TEMP_DIR} | grep .sqlite)
SQLITE_REQUEST="select name from packages where rpm_sourcerpm like '${PACKAGENAME}-%.rpm';"
PACKAGES=$(sqlite3 "${CENTOS_TEMP_DIR}/${SQLITE_FILE}" "${SQLITE_REQUEST}")

for package in ${PACKAGES[@]}; do
    fields="name,version,release"
    request="select ${fields} from packages where name = '${package}';"
    package_info=$(sqlite3 "${CENTOS_TEMP_DIR}/${SQLITE_FILE}" "${request}")
    release_regex="mos\K(\d+)"
    bin_release=$(echo $package_info | awk -F '|' '{print $3}' | grep -oP $release_regex)

    #--------------------------------------------------------------------
    # Step 7 : Check if release is the same
    #--------------------------------------------------------------------
    if [ "$bin_release" = "$GERRIT_MOS_RELEASE" ]; then
        echo "${package} - mos${bin_release} - CONSISTENT"
    else
        echo "${package} - mos${bin_release} - INCOSISTENT"
    fi

done
exit 0;
# FIXME : Check all the packages from the list. Or get the list form repo
#PACKAGES_LIST=$(grep ${PACKAGE_NAME} ./projects.txt |awk '{print $1}')

if [ "$BIN_MOS_RELEASE" = "$GERRIT_MOS_RELEASE" ]; then
    echo "CONSISTENT!"
else
    echo "INCOSISTENT"
fi
