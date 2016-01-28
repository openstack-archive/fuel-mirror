#!/bin/bash

#set -ex

#***********************************************************************************************
#Input properties
PACKAGE_NAME="ironic-api"
UBUNTU_REPO="perestroika-repo-tst.infra.mirantis.net/mos-repos/ubuntu/8.0"
TEMP_DIR="./tmp"
SRC_DIR="./src"
#============================================================================


if [ -d "$TEMP_DIR" ]; then
    rm -rf $TEMP_DIR
fi

mkdir $TEMP_DIR

UBUNTU_RELEASE_DOWNLOAD_PATH="${UBUNTU_REPO}/dists/mos8.0/Release"
UBUNTU_RELEASE_FILE="${TEMP_DIR}/Release"

wget -O $UBUNTU_RELEASE_FILE $UBUNTU_RELEASE_DOWNLOAD_PATH

ARCHS=$(awk -F ':' '/Architectures/ {print $2}' $UBUNTU_RELEASE_FILE)

for arch in $ARCHS; do
    UBUNTU_PACKAGE_DOWNLOAD_PATH="${UBUNTU_REPO}/dists/mos8.0/main/binary-${arch}/Packages"
    UBUNTU_PACKAGE_FILE="${TEMP_DIR}/Packages-$arch"

    wget -O $UBUNTU_PACKAGE_FILE $UBUNTU_PACKAGE_DOWNLOAD_PATH

done

echo "Package file: $UBUNTU_PACKAGE_FILE"

#Get date from Release file
DATE_STAMP=$(grep ^Date: ${UBUNTU_RELEASE_FILE}| awk -F ':' '{print $2":"$3":"$4}' | awk -F ' ' '{print $2, $3, $4, $5, $6}' | xargs -0 date "+%Y-%m-%d %H:%M:%S" -d)
TIME_BEFORE=$(date "+%Y-%m-%d %H:%M:00" --date "${DATE_STAMP} 1 minutes")

echo "Date: ${DATE_STAMP}"

GERRIT_HOST="review.fuel-infra.org"
GERRIT_PORT="29418"
GERRIT_USER="dmoisa"
GERRIT_PROJECT=$(grep ${PACKAGE_NAME} ./projects.txt |awk '{print $2}')
GERRIT_QUERY_FORMAT="TEXT"
GERRIT_QUERY_LIMIT="1"
GERRIT_COMMIT_INFO_FILE_PATH="./tmp/commit_info.txt"
GERRIT_PROJECT_NAME=$(echo $GERRIT_PROJECT|awk -F '/' '{print $2}')
GERRIT_PROJECT_URL="ssh://${GERRIT_USER}@${GERRIT_HOST}:${GERRIT_PORT}/${GERRIT_PROJECT}"

PACKAGE_START_LINE=$(grep -n "Package:.*$PACKAGE_NAME" $UBUNTU_PACKAGE_FILE | awk -F ':' '{print $1}')
PACKAGE_END_LINE=$((PACKAGE_START_LINE+15)) #FIXME: magic number
PACKAGE_VERSION=$(awk -v from=$PACKAGE_START_LINE -v to=$PACKAGE_END_LINE 'NR>=from && NR<=to && /Version:/ {print $2}' $UBUNTU_PACKAGE_FILE)

#?????????????????????????????????????????????????????????????????????
# FIXME : Check all the packages from the list. Or get the list form 
#         repo
PACKAGES_LIST=$(grep ${PACKAGE_NAME} ./projects.txt |awk '{print $1}')
#?????????????????????????????????????????????????????????????????????

echo "*****************************************"
echo "Package: ${PACKAGE_NAME}"
echo "Version: $PACKAGE_VERSION"
echo "Repo: ${UBUNTU_REPO}"
echo "Gerrit project: ${GERRIT_PROJECT}"
echo "Gerrit project name: ${GERRIT_PROJECT_NAME}"
echo "-----------------------------------------"
echo "Commit time to look: ${TIME_BEFORE}"

PROJECT_SRC_DIR="${SRC_DIR}/${GERRIT_PROJECT_NAME}"

if [ -d "$PROJECT_SRC_DIR" ]; then
    echo "Deleting $PROJECT_SRC_DIR"
    rm -rf $PROJECT_SRC_DIR
fi

echo "Clonning ${GERRIT_PROJECT_URL} to ${PROJECT_SRC_DIR}"
$(git clone ${GERRIT_PROJECT_URL} $PROJECT_SRC_DIR)

GERRIT_QUERY_COMMAND="ssh -p ${GERRIT_PORT} ${GERRIT_USER}@${GERRIT_HOST} gerrit query --format=${GERRIT_QUERY_FORMAT} --current-patch-set project:{${GERRIT_PROJECT}} before:{$TIME_BEFORE} status:merged limit:${GERRIT_QUERY_LIMIT}"
echo "${GERRIT_QUERY_COMMAND}"
$( $GERRIT_QUERY_COMMAND > $GERRIT_COMMIT_INFO_FILE_PATH )

GERRIT_REFSPEC=$(grep 'ref:' $GERRIT_COMMIT_INFO_FILE_PATH | awk '{print $2}')
GERRIT_MERGEDTO=$(grep 'branch:' $GERRIT_COMMIT_INFO_FILE_PATH | awk '{print $2}')
echo "Gerrit refspec: $GERRIT_REFSPEC"
echo "Merged to: $GERRIT_MERGEDTO"

GERRIT_FETCH_COMMAND="git fetch ${GERRIT_PROJECT_URL} ${GERRIT_REFSPEC} && git checkout FETCH_HEAD"
echo "${GERRIT_FETCH_COMMAND}"
$(git -C $PROJECT_SRC_DIR fetch ${GERRIT_PROJECT_URL} ${GERRIT_REFSPEC} && git -C $PROJECT_SRC_DIR checkout FETCH_HEAD)

#FIXME: if not Fuel
TAG_REGEX="\d+\.\d+\.\d+"
RELEASE_TAG=$(echo $PACKAGE_VERSION | grep -oP "\d+\.\d+\.\d+")
echo "Tag: $RELEASE_TAG"
MOS_VERSION_REGEX="mos\K(\d+)"
BIN_MOS_VERSION=$(echo $PACKAGE_VERSION | grep -oP $MOS_VERSION_REGEX)
echo "Bin mos version: $BIN_MOS_VERSION"

GERRIT_MOS_VERSION=$(git -C ${PROJECT_SRC_DIR} rev-list --no-merges ${RELEASE_TAG}..origin/${GERRIT_MERGEDTO} | wc -l)
echo "Mos version: $GERRIT_MOS_VERSION"

if [ "$BIN_MOS_VERSION" -eq "$GERRIT_MOS_VERSION" ]; then
    echo "CONSISTENT!"
else
    echo "INCOSISTENT"
fi
