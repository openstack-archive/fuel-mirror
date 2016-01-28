#!/bin/bash

#set -ex

#***********************************************************************************************
#Input properties
PACKAGE_NAME="openstack-cinder"
CENTOS_REPO="perestroika-repo-tst.infra.mirantis.net/mos-repos/centos/mos8.0-centos7-fuel"
TEMP_DIR="./tmp"
SRC_DIR="./src"
#============================================================================


if [ -d "$TEMP_DIR" ]; then
    rm -rf $TEMP_DIR
fi

mkdir $TEMP_DIR
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

TIMESTAMP_TAG_REGEXP="<timestamp>\K(\d+)"
REPOMD_START_LINE=$(grep -onP "${XML_BZNAME_REGEX}"  "${TEMP_DIR}/repomd.xml" | awk -F ':' '{print $1}')
REPOMD_UPDATE_UTIME=$(tail -n +${REPOMD_START_LINE} ${TEMP_DIR}/repomd.xml | grep -oP -m 1 "$TIMESTAMP_TAG_REGEXP")
TIME_BEFORE=$(date "+%Y-%m-%d %H:%M:00" --date @${REPOMD_UPDATE_UTIME})

SQLITE_FILE=$(ls ${TEMP_DIR} | grep .sqlite)
SQLITE_FIELDS="name,version,release"
SQLITE_REQUEST="select ${SQLITE_FIELDS} from packages where name = '${PACKAGE_NAME}';"
PACKAGE_INFO=$(sqlite3 "${TEMP_DIR}/${SQLITE_FILE}" "${SQLITE_REQUEST}")
echo "$PACKAGE_INFO"

PACKAGE_VERSION=$(echo $PACKAGE_INFO | awk -F '|' '{print $2}')

echo "Date: ${TIME_BEFORE}"

GERRIT_HOST="review.fuel-infra.org"
GERRIT_PORT="29418"
GERRIT_USER="dmoisa"
GERRIT_PROJECT=$(grep ${PACKAGE_NAME} ./projects.txt |awk '{print $2}')
GERRIT_QUERY_FORMAT="TEXT"
GERRIT_QUERY_LIMIT="1"
GERRIT_COMMIT_INFO_FILE_PATH="./tmp/commit_info.txt"
GERRIT_PROJECT_NAME=$(echo $GERRIT_PROJECT|awk -F '/' '{print $2}')
GERRIT_PROJECT_URL="ssh://${GERRIT_USER}@${GERRIT_HOST}:${GERRIT_PORT}/${GERRIT_PROJECT}"


#?????????????????????????????????????????????????????????????????????
# FIXME : Check all the packages from the list. Or get the list form 
#         repo
PACKAGES_LIST=$(grep ${PACKAGE_NAME} ./projects.txt |awk '{print $1}')
#?????????????????????????????????????????????????????????????????????

echo "*****************************************"
echo "Package: ${PACKAGE_NAME}"
echo "Version: $PACKAGE_VERSION"
echo "Repo: ${CENTOS_REPO}"
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

MOS_RELEASE=$(echo ${PACKAGE_INFO} | awk -F '|' '{print $3}')

MOS_VERSION_REGEX="mos\K(\d+)"
BIN_MOS_VERSION=$(echo $MOS_RELEASE | grep -oP $MOS_VERSION_REGEX)

echo "Bin mos version: $BIN_MOS_VERSION"

GERRIT_MOS_VERSION=$(git -C ${PROJECT_SRC_DIR} rev-list --no-merges ${RELEASE_TAG}..origin/${GERRIT_MERGEDTO} | wc -l)
echo "Mos version: $GERRIT_MOS_VERSION"

if [ "$BIN_MOS_VERSION" -eq "$GERRIT_MOS_VERSION" ]; then
    echo "CONSISTENT!"
else
    echo "INCOSISTENT"
fi
