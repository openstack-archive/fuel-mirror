#!/bin/bash -ex

SCRIPT_DIR="$(dirname $(readlink -e $0))"

[ -f ".publisher-defaults-rpm" ] && source .publisher-defaults-rpm
source "${SCRIPT_DIR}/functions/publish-functions.sh"
source "${SCRIPT_DIR}/functions/locking.sh"




# Used global envvars
# ======================================================
#
#
# Mixed from publish-functions.sh
# ------------------------------------------------------
#
# TMP_DIR                   path to temporary directory
# WRK_DIR                   path to current working directory
#
#
# Input parameters for downloading package(s) from given jenkins-worker
# ------------------------------------------------------
#
# SSH_OPTS                  ssh options for rsync (could be empty)
# SSH_USER                  user who have ssh access to the worker (could be empty)
# BUILD_HOST                fqdn/ip of worker
# PKG_PATH                  path to package which should be download
#
#
# Patchset-related parameters
# ------------------------------------------------------
# LP_BUG                    string representing ref. to bug on launchpad
#                           used for grouping packages related to
#                           the same bug into one repository (3)
# GERRIT_CHANGE_STATUS      status of patchset, actually only "NEW" matters
# GERRIT_PATCHSET_REVISION  revision of patchset, used only in rendering
#                           final artifact (deb.publish.setenvfile)
# REQUEST_NUM               identifier of request CR-12345 (3)
#
# Security-related parameters
# ------------------------------------------------------
# SIGKEYID           user used for signing release files
# PROJECT_NAME       project name used for saving key file
# PROJECT_VERSION    project name used for saving key file
#
#
# DIST                      Name of OS distributive (centos7, for ex.)
#
# Repository naming
# It's possible to provide overrides which should be used
# as names for proposed, secutity, updates and holdback repositories
# DEB_DIST_NAME will be used if no overrides given
# ------------------------------------------------------
# RPM_OS_REPO_PATH          name of "main" repository repo (for ex. mos8.0)
# RPM_PROPOSED_REPO_PATH    name of "proposed" repository repo (for ex. mos8.0-proposed) (optional)
# RPM_UPDATES_REPO_PATH     name of "updates" repository repo (for ex. mos8.0-updates) (optional)
# RPM_SECURITY_REPO_PATH    name of "security" repository repo (for ex. mos8.0-security) (optional)
# RPM_HOLDBACK_REPO_PATH    name of "holdback" repository repo (for ex. mos8.0-holdback) (optional)
#
# Directives for using different kinds of workflows which
# define output repos/component name for packages
# (will be applied directive with highest priority)
# ------------------------------------------------------
# IS_UPDATES         p1. updates workflow -> publish to proposed repo
# IS_HOLDBACK        p2. holdback workflow -> publish to holdback repo (USE WITH CARE!)
# IS_SECURITY        p3. security workflow -> publish to security repo
# IS_RESTRICTED      is not implemented !
# IS_DOWNGRADE       downgrade package: remove ONE previously published version of this package
#
#    USER
# REMOTE_REPO_HOST
# CUSTOM_REPO_ID
# SIGKEYID
# REPO_REQUEST_PATH_PREFIX
# DEFAULTCOMPSXML
# REPO_BASE_PATH


_sign_rpm() {
    # ``rpmsign`` is interactive command and couldn't be called in direct way,
    # so here used ``expect`` for entering passphrase
    # params:
    # $1 -> sigkeyid
    # $2 -> path to binary to resign
    # --------------------------------------------------

    LANG=C expect <<EOL
spawn rpmsign --define "%__gpg_check_password_cmd /bin/true" --define "%_signature gpg" --define "%_gpg_name $1" --resign $2
expect -exact "Enter pass phrase:"
send -- "Doesn't matter\r"
expect eof
lassign [wait] pid spawnid os_error_flag value
puts "exit status: \$value"
exit \$value
EOL
    exit $?
}



main() {

    # Preparations
    # ==================================================

    # Check if it's possible to sign packages
    # --------------------------------------------------

    if [ -n "${SIGKEYID}" ] ; then
        check-gpg || :
        gpg --export -a "${SIGKEYID}" > RPM-GPG-KEY
        if [ $(rpm -qa | grep gpg-pubkey | grep -ci "${SIGKEYID}") -eq 0 ]; then
            rpm --import RPM-GPG-KEY
        fi
    fi


    # Reinitialize temp directory
    # --------------------------------------------------

    recreate_tmp_dir


    # Download package from worker
    # ==================================================


    # fixme: Looks like we have a bug here and user and host should be separated.
    #        We didn't shoot-in-the leg IRL because we don't pass this param
    #        Prop. sol: [ -z "${SSH_USER}" ] && SSH_USER="${SSH_USER}@"

    rsync -avPzt                                        \
          -e "ssh -o StrictHostKeyChecking=no           \
                  -o UserKnownHostsFile=/dev/null       \
                  ${SSH_OPTS}"                          \
          "${SSH_USER}${BUILD_HOST}:${PKG_PATH}/"       \
          "${TMP_DIR}/"                                 \
    || error "Can't download packages"

    # fixme: this check is performed for rpm, but missed in deb, why?
    [ $(ls -1 ${TMP_DIR}/ | wc -l) -eq 0 ] && error "Can't download packages"


    # Initialization of repositories
    # Here we create repo which will be filled next
    # ==================================================

    # Crunch for using custom namespace for publishing packages
    # When CUSTOM_REPO_ID is given, then:
    # - packages are not grouped by bug
    # - CUSTOM_REPO_ID is used instead of request serial number
    if [ -n "${CUSTOM_REPO_ID}" ] ; then
        unset LP_BUG
        REQUEST_NUM="${CUSTOM_REPO_ID}"
    fi

    # Configuring paths and namespaces:
    # - only newly created patchsets have prefixes
    # - if LP_BUG is given then it replaces REQUEST_NUM ("Grouping" feature)
    # ---------------------------------------------------

    local LOCAL_REPO_BASE_PATH=
    local URL_PREFIX=

    if [ "${GERRIT_CHANGE_STATUS}" == "NEW" ] ; then
        if [ -n "${LP_BUG}" ] ; then
            LOCAL_REPO_BASE_PATH="${REPO_BASE_PATH}/${REPO_REQUEST_PATH_PREFIX}${LP_BUG}"
            URL_PREFIX="${REPO_REQUEST_PATH_PREFIX}${LP_BUG}/"
        else
            LOCAL_REPO_BASE_PATH="${REPO_BASE_PATH}/${REPO_REQUEST_PATH_PREFIX}${REQUEST_NUM}"
            URL_PREFIX="${REPO_REQUEST_PATH_PREFIX}${REQUEST_NUM}/"
        fi
    else
        LOCAL_REPO_BASE_PATH="${REPO_BASE_PATH}"
        URL_PREFIX=""
    fi


    # Create all repositories
    # ---------------------------------------------------

    for repo_path in "${RPM_OS_REPO_PATH}"       \
                     "${RPM_PROPOSED_REPO_PATH}" \
                     "${RPM_UPDATES_REPO_PATH}"  \
                     "${RPM_SECURITY_REPO_PATH}" \
                     "${RPM_HOLDBACK_REPO_PATH}" ; do

        local _full_repo_path="${LOCAL_REPO_BASE_PATH}/${repo_path}"

        if [ ! -d "${_full_repo_path}" ] ; then

            mkdir -p "${_full_repo_path}/{x86_64/Packages,Source/SPackages,x86_64/repodata}"

            job_lock "${_full_repo_path}.lock" wait 3600

                createrepo --pretty                     \
                           --database                   \
                           --update                     \
                           -o "${_full_repo_path}/x86_64/" "${_full_repo_path}/x86_64"

                createrepo --pretty                     \
                           --database                   \
                           --update                     \
                           -o "${_full_repo_path}/Source/" "${_full_repo_path}/Source"

            job_lock "${_full_repo_path}.lock" unset
        fi

    done


    # Defining repository name
    # Here we determine where to put new packages
    # ==================================================

    # Fill in all the defaults
    # when some parameters are not given then fallback to "main" path
    # --------------------------------------------------

    [ -z "${RPM_UPDATES_REPO_PATH}" ] && RPM_UPDATES_REPO_PATH="${RPM_OS_REPO_PATH}"
    [ -z "${RPM_PROPOSED_REPO_PATH}" ] && RPM_PROPOSED_REPO_PATH="${RPM_OS_REPO_PATH}"
    [ -z "${RPM_SECURITY_REPO_PATH}" ] && RPM_SECURITY_REPO_PATH="${RPM_OS_REPO_PATH}"
    [ -z "${RPM_HOLDBACK_REPO_PATH}" ] && RPM_HOLDBACK_REPO_PATH="${RPM_OS_REPO_PATH}"


    # By default publish into main repository
    # --------------------------------------------------

    LOCAL_RPM_REPO_PATH="${RPM_OS_REPO_PATH}"


    # Processing different kinds of input directives "IS_XXX"
    # --------------------------------------------------


    # Updates workflow:
    # all built packages should be put into proposed repository
    # after tests and acceptance they are published to updates by other tools
    # --------------------------------------------------

    if [ "${IS_UPDATES}" = 'true' ] ; then
        LOCAL_RPM_REPO_PATH="${RPM_PROPOSED_REPO_PATH}"
    fi

    # Holdback workflow:
    # all built packages should be put into holdback repository
    # this wotkflow should be used in esceeptional cases
    # --------------------------------------------------

    if [ "${IS_HOLDBACK}" == 'true' ] ; then
        LOCAL_RPM_REPO_PATH="${RPM_HOLDBACK_REPO_PATH}"
    fi


    # Security workflow:
    # all built packages should be put into security repository
    # this is short-circuit for delivering security updates beside long updates workflow
    # --------------------------------------------------
    if [ "${IS_SECURITY}" == 'true' ] ; then
        LOCAL_RPM_REPO_PATH="${RPM_SECURITY_REPO_PATH}"
    fi

    local LOCAL_REPO_PATH="${LOCAL_REPO_BASE_PATH}/${LOCAL_RPM_REPO_PATH}"


    # Filling of repository with new files
    # ==================================================


    # Aggregate list of files for further processing
    # --------------------------------------------------

    local NEW_SRC_PKG_PATH=""
    local NEW_SRC_PKG_FILE=""

    local NEW_BIN_PKG_PATHS=""
    local NEW_BIN_PKG_FILES=""

    for _file in ${TMP_DIR}/* ; do
        if [ "${_file:(-7)}" == "src.rpm" ] ; then
            NEW_SRC_PKG_PATH="${_file}"
            NEW_SRC_PKG_FILE="${_file##*/}"
        elif [ "${_file##*.}" == "rpm" ]; then
            NEW_BIN_PKG_PATHS="${NEW_BIN_PKG_PATHS} ${_file}"
            NEW_BIN_PKG_FILES="${NEW_BIN_PKG_FILES} ${_file##*/}"
        fi
    done

    # Binaries to compare
    NEW_PKG_FILES="${NEW_SRC_PKG_FILE} ${NEW_BIN_PKG_FILES}"

    local NEW_BIN_PKG_NAMES=""

    # Get existing srpm filename
    local OLD_SRC_PKG_NAME="$(                          \
        rpm -qp                                         \
            --queryformat "%{NAME}" ${NEW_SRC_PKG_PATH} \
    )"

    local _repoid_source="$(mktemp -u XXXXXXXX)"

    local OLD_SRC_PKG_PATH="$(                          \
        repoquery --repofrompath=${_repoid_source},file://${LOCAL_REPO_PATH}/Source/ \
                  --repoid=${_repoid_source}            \
                  --archlist=src                        \
                  --location ${OLD_SRC_PKG_NAME}        \
    )"

    local OLD_SRC_PKG_FILE="${OLD_SRC_PKG_PATH##*/}"

    # Get existing rpm files
    local OLD_BIN_PKG_FILE="$(                          \
        python "${SCRIPT_DIR}/repoquerysrpm.py"         \
               --srpm=${OLD_SRC_PKG_FILE}               \
               --path=${LOCAL_REPO_PATH}/x86_64/        \
        | awk -F'/' '{print $NF}'                       \
    )"

    # Cleanup `repoquery` data
    find /var/tmp/yum-${USER}-*                         \
         -type d                                        \
         -name ${_repoid_source}                        \
         -exec rm -rf {} \;                             \
         2>/dev/null                                    \
    || true

    job_lock "${LOCAL_REPO_PATH}.lock" wait 3600

        # Sign and publish binaries
        for new_pkg_path in ${NEW_BIN_PKG_PATHS} \
                            ${NEW_SRC_PKG_PATH}     ; do

            local PACKAGEFOLDER=

            if [ "${new_pkg_path:(-7)}" == "src.rpm" ] ; then
                PACKAGEFOLDER="Source/SPackages"
            else
                PACKAGEFOLDER="x86_64/Packages"
            fi

            # Get package info
            local NEW_BINDATA="$(                       \
                rpm -qp                                 \
                    --queryformat "%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{SHA1HEADER}\n" \
                    ${new_pkg_path}                     \
                    2>/dev/null                         \
            )"

            local _arr=($(echo "${NEW_BINDATA}"))

            # splitting result into variables:
            local NEW_BINEPOCH="${_arr[1]}"
            local BINNAME="${_arr[2]}"
            local NEW_BINVERSION="${_arr[3]}"
            local NEW_BINRELEASE="${_arr[4]}"
            local NEW_BINSHA="${_arr[5]}"

            if [ "${NEW_BINEPOCH}" == "(none)" ] ; then
                NEW_BINEPOCH='0'
            fi

            if [ "${new_pkg_path:(-7)}" != "src.rpm" ] ; then
                # append src.rpm packages to list
                NEW_BIN_PKG_NAMES="${NEW_BIN_PKG_NAMES} ${BINNAME}"
            fi


            local _repoid_os="$(mktemp -u XXXXXXXX)"
            local _repoid_updates="$(mktemp -u XXXXXXXX)"
            local _repoid_proposed="$(mktemp -u XXXXXXXX)"
            local _repoid_holdback="$(mktemp -u XXXXXXXX)"
            local _repoid_security="$(mktemp -u XXXXXXXX)"

            local _additional_param=""
            if [ "${new_pkg_path:(-7)}" == "src.rpm" ] ; then
                _additional_param="--archlist=src"
            fi

            local repoquery_cmd="repoquery \
                --repofrompath=${_repoid_os},file://${LOCAL_REPO_BASE_PATH}/${RPM_OS_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_os} \
                --repofrompath=${_repoid_updates},file://${LOCAL_REPO_BASE_PATH}/${RPM_UPDATES_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_updates} \
                --repofrompath=${_repoid_proposed},file://${LOCAL_REPO_BASE_PATH}/${RPM_PROPOSED_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_proposed} \
                --repofrompath=${_repoid_holdback},file://${LOCAL_REPO_BASE_PATH}/${RPM_HOLDBACK_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_holdback} \
                --repofrompath=${_repoid_security},file://${LOCAL_REPO_BASE_PATH}/${RPM_SECURITY_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_security} \
                ${_additional_param}"

            unset _additional_param


            local OLD_BINDATA="$(                       \
                ${repoquery_cmd} ${BINNAME}             \
                                 2>/dev/null            \
            )"

            # Cleanup `repoquery` data
            for _repoid in ${_repoid_os}       \
                           ${_repoid_updates}  \
                           ${_repoid_proposed} \
                           ${_repoid_holdback} \
                           ${_repoid_security} ; do

                # remove by pattern
                find "/var/tmp/yum-${USER}-*"           \
                     -type d                            \
                     -name "${_repoid}"                 \
                     -exec rm -rf {} \;                 \
                     2>/dev/null                        \
                || true

            done

            # Determine
            # - epoch,
            # - version and
            # - release.
            # These parameters are required for comparing existing package with new one.
            #
            # Below is complicated code related to splitting name of package into
            # parts which represent different parameters of that package.
            #
            # Here is sample workflow of splitting such line:
            #
            # python-oslo-messaging-0:2.5.0-4.el7~mos16.git.196de7f.54be4a8.noarch
            #                                                               ^^^^^^ ---> OLD_BINARCH
            # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^------- ---> OLD_BINDATA
            #                       ^--------------------------------------------- ---> OLD_BINEPOCH
            #                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^------- ---> OLD_BINDATA
            #                         ^^^^^--------------------------------------- ---> OLD_BINVERSION
            #                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^------- ---> OLD_BINRELEASE
            #
            # note: git.196de7f.54be4a8 is optional part and not used after 8.0 release
            # note: OLD_BINDATA actually isn't required - it's a temp var
            # --------------------------------------------------


            local OLD_BINARCH="${OLD_BINDATA##*.}"

            # Skip arch
            local OLD_BINDATA="${OLD_BINDATA%.*}"

            local OLD_BINEPOCH="$(                      \
                echo ${OLD_BINDATA}                     \
                | cut -d':' -f1                         \
                | awk -F'-' '{print $NF}'               \
            )"

            # Skip "pkg-name-epoch:"
            local OLD_BINDATA="${OLD_BINDATA#*:}"

            local OLD_BINVERSION="${OLD_BINDATA%%-*}"

            local OLD_BINRELEASE="${OLD_BINDATA#*-}"


            ## FixMe: Improve packages removing
            # Remove existing packages from repo (for new change requests and downgrades)
            if [ "${GERRIT_CHANGE_STATUS}" == "NEW" -o "${IS_DOWNGRADE}" == "true" ] ;  then

                # fixme: do we have a bug here?
                # pattern could look like this
                # - no package found:
                #   python-oslo-messaging--.*

                local _old_pkg_file_pattern="${BINNAME}-${OLD_BINVERSION}-${OLD_BINRELEASE}.${OLD_BINARCH}*"

                find ${LOCAL_REPO_PATH}                 \
                     -name "${_old_pkg_file_pattern}"   \
                     -exec rm -f {} \;
                unset OLD_BINVERSION
            fi

            # Compare versions of new and existring packages

            local SKIPPACKAGE="no"

            if [ ! -z "${OLD_BINVERSION}" ] ; then

                # Comparing versions before including package to the repo
                # When we have deal with the same package, we could skip it and don't publish
                # --------------------------------------

                local CMPVER="$(                        \
                    A_EPOCH="${OLD_BINEPOCH}"           \
                    A_VERSION="${OLD_BINVERSION}"       \
                    A_RELEASE="${OLD_BINRELEASE}"       \
                    B_EPOCH="${NEW_BINEPOCH}"           \
                    B_VERSION="${NEW_BINVERSION}"       \
                    B_RELEASE="${NEW_BINRELEASE}"       \
                    python "${SCRIPT_DIR}/cmp_evr.py"   \
                )"

                # Results:
                #  1 - OLD_BIN is newer than NEW_BIN
                #  0 - OLD_BIN and NEW_BIN have the same version
                # -1 - OLD_BIN is older than NEW_BI

                local _old_pkg_name="${BINNAME}-${OLD_BINEPOCH}:${OLD_BINVERSION}-${OLD_BINRELEASE}"

                case "${CMPVER}" in
                    1)

                        error "Can't publish ${new_pkg_path#*/}. Existing ${_old_pkg_name} has newer version"
                    ;;

                    0)  # Check sha for identical package names

                        OLD_RPMFILE=$(${repoquery_cmd} --location ${BINNAME})
                        OLD_BINSHA=$(rpm -qp --queryformat "%{SHA1HEADER}" ${OLD_RPMFILE})

                        if [ "${NEW_BINSHA}" == "${OLD_BINSHA}" ]; then
                            SKIPPACKAGE="yes"
                            info "Skipping including of ${new_pkg_path}. Existing ${_old_pkg_name} has the same version and checksum"
                        else
                            error "Can't publish ${new_pkg_path#*/}. Existing ${_old_pkg_name} has the same version but different checksum"
                        fi
                    ;;

                    *)
                        true
                    ;;
                esac

            fi

            # Signing
            # ------------------------------------------

            if [ -n "${SIGKEYID}" ] ; then
                _sign_rpm "${SIGKEYID}" "${new_pkg_path}"

                if [ $? -ne 0 ] ; then
                    error "Something went wrong. Can't sign package ${new_pkg_path#*/}"
                fi
            fi

            # fixme: why did we signed package if we don't want to include it into repo?

            if [ "${SKIPPACKAGE}" == "no" ] ; then
                cp "${new_pkg_path}" "${LOCAL_REPO_PATH}/${PACKAGEFOLDER}"
            fi

        done


        # Cleanup files from previous version
        # When packages are replaced, there could stay some artifacts
        # from previously published version, so it's required to clean them.
        #
        # ----------------------------------------------

        for _old_pkg_file in ${OLD_SRC_PKG_FILE} \
                             ${OLD_BIN_PKG_FILE} ; do

            # note: construction below means "if _old_pkg_file not in NEW_PKG_FILES"
            if [ "${NEW_PKG_FILES}" == "${NEW_PKG_FILES/$_old_pkg_file/}" ] ; then
                find "${LOCAL_REPO_PATH}"               \
                     -type f                            \
                     -name ${_old_pkg_file}             \
                     -exec rm {} \;                     \
                     2>/dev/null
            fi

        done

        # Keep only latest packages

        rm -f "$(repomanage --keep=1 --old "${LOCAL_REPO_PATH}/x86_64")"
        rm -f "$(repomanage --keep=1 --old "${LOCAL_REPO_PATH}/Source")"

        # Update and sign repository metadata
        # ----------------------------------------------

        if [ ! -e "${LOCAL_REPO_PATH}/comps.xml" ] ; then

            if [ -z "${DEFAULTCOMPSXML}" ] ; then
                DEFAULTCOMPSXML="http://mirror.fuel-infra.org/fwm/6.0/centos/os/x86_64/comps.xml"
            fi

            wget "${DEFAULTCOMPSXML}" -O "${LOCAL_REPO_PATH}/comps.xml"

        fi

        createrepo --pretty                             \
                   --database                           \
                   --update                             \
                   -g ${LOCAL_REPO_PATH}/comps.xml      \
                   -o ${LOCAL_REPO_PATH}/x86_64/ ${LOCAL_REPO_PATH}/x86_64

        createrepo --pretty                             \
                   --database                           \
                   --update                             \
                   -o ${LOCAL_REPO_PATH}/Source/ ${LOCAL_REPO_PATH}/Source


        if [ -n "${SIGKEYID}" ] ; then

            rm -f "${LOCAL_REPO_PATH}/x86_64/repodata/repomd.xml.asc"
            rm -f "${LOCAL_REPO_PATH}/Source/repodata/repomd.xml.asc"

            gpg --armor                                 \
                --local-user ${SIGKEYID}                \
                --detach-sign ${LOCAL_REPO_PATH}/x86_64/repodata/repomd.xml

            gpg --armor                                 \
                --local-user ${SIGKEYID}                \
                --detach-sign ${LOCAL_REPO_PATH}/Source/repodata/repomd.xml

            if [ -f "RPM-GPG-KEY" ] ; then
                cp "RPM-GPG-KEY" "${LOCAL_REPO_PATH}/RPM-GPG-KEY-${PROJECT_NAME}${PROJECT_VERSION}"
            fi

        fi

        # Sync repo to remote host
        sync-repo "${LOCAL_REPO_PATH}/" "${LOCAL_RPM_REPO_PATH}" "${REPO_REQUEST_PATH_PREFIX}" "${REQUEST_NUM}" "${LP_BUG}"

    job_lock ${LOCAL_REPO_PATH}.lock unset


    # Filling report file and export results
    # ==================================================


    local RPM_VERSION="${NEW_BINEPOCH}:${NEW_BINVERSION}-${NEW_BINRELEASE}"
    local RPM_REPO_URL="http://${REMOTE_REPO_HOST}/${URL_PREFIX}${LOCAL_RPM_REPO_PATH}/x86_64"
    local RPM_BINARIES="$(                              \
        echo ${NEW_BIN_PKG_NAMES}                       \
        | sed 's|^ ||; s| |,|g'                         \
    )"

    local rep_file="${WRK_DIR}/rpm.publish.setenvfile"
    rm -f "${rep_file}"

    # Report:
    # --------------------------------------------------

    info "Creating report in ${rep_file}"

    echo                                     > "${rep_file}"
    echo "RPM_PUBLISH_SUCCEEDED=true"       >> "${rep_file}"
    echo "RPM_DISTRO=${DIST}"               >> "${rep_file}"
    echo "RPM_VERSION=${RPM_VERSION}"       >> "${rep_file}"
    echo "RPM_REPO_URL=${RPM_REPO_URL}"     >> "${rep_file}"
    echo "RPM_BINARIES=${RPM_BINARIES}"     >> "${rep_file}"
    echo "RPM_CHANGE_REVISION=${GERRIT_PATCHSET_REVISION}" \
                                            >> "${rep_file}"
    echo "LP_BUG=${LP_BUG}"                 >> "${rep_file}"

    # --------------------------------------------------
}

main
exit 0
