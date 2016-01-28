#===============================================================================================
#                                          FUNCTIONS
#===============================================================================================

# Description:
#     Get Gerrit patch-set for the required package by timestamp
# Input:
#     GERRIT_PORT         << properties.sh
#     GERRIT_USER         << properties.sh
#     GERRIT_HOST         << properties.sh
#     GERRIT_QUERY_FORMAT << properties.sh
#     GERRIT_QUERY_LIMIT  << properties.sh
#     GERRIT_COMMIT_INFO_FILE_PATH <<properties.sh
#     SRC_PROJECT
#     TIME_BEFORE
# Output:
#     GERRIT_PROJECT_URL
#     GERRIT_PROJECT_NAME
#     GERRIT_REFSPEC
#     GERRIT_MERGEDTO
get_gerrit_properties () {

    ssh -p $GERRIT_PORT ${GERRIT_USER}@${GERRIT_HOST} gerrit query --format=$GERRIT_QUERY_FORMAT --current-patch-set project:{$SRC_PROJECT} before:{$TIME_BEFORE} status:merged limit:$GERRIT_QUERY_LIMIT > $GERRIT_COMMIT_INFO_FILE_PATH

    GERRIT_PROJECT_URL="ssh://${GERRIT_USER}@${GERRIT_HOST}:${GERRIT_PORT}/${SRC_PROJECT}"
    GERRIT_PROJECT_NAME=$(echo $SRC_PROJECT|awk -F '/' '{print $2}')
    GERRIT_REFSPEC=$(grep 'ref:' $GERRIT_COMMIT_INFO_FILE_PATH | awk '{print $2}')
    GERRIT_MERGEDTO=$(grep 'branch:' $GERRIT_COMMIT_INFO_FILE_PATH | awk '{print $2}')
}

# Description:
#     Get sources from Gerrit of the required state
# Input:
#     GERRIT_PROJECT_URL
#     PROJECT_SRC_DIR
#     GERRIT_REFSPEC
get_gerrit_patchset () {
    git clone $GERRIT_PROJECT_URL $PROJECT_SRC_DIR
    git -C $PROJECT_SRC_DIR fetch ${GERRIT_PROJECT_URL} ${GERRIT_REFSPEC} && git -C $PROJECT_SRC_DIR checkout FETCH_HEAD
}

# Description:
#     Get package release from sources
# Input:
#     PROJECT_SRC_PSTH
#     GERRIT_MERGEDTO
# Output:
#     GERRIT_MOS_RELEASE
get_package_release () {
    local release_tag=$(git -C ${PROJECT_SRC_DIR} describe --abbrev=0)
    GERRIT_MOS_RELEASE=$(git -C ${PROJECT_SRC_DIR} rev-list --no-merges ${release_tag}..origin/${GERRIT_MERGEDTO} | wc -l)
}

get_deb_package_release () {
    get_package_release
}

get_fuel_deb_package_version () {
  version=$(git -C ${srcpath} rev-list --no-merges origin/${SOURCE_BRANCH} | wc -l)
}

get_rpm_package_release () {
    get_package_release
}

#TBD
get_fuel_rpm_package_version () {
   echo "NOT IMPLEMENTED"
}
