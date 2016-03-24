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

# ~~~~~~~~~~~
#    RPM_OS_REPO_PATH
#    RPM_UPDATES_REPO_PATH
#    RPM_PROPOSED_REPO_PATH
#    RPM_SECURITY_REPO_PATH
#    RPM_HOLDBACK_REPO_PATH
#    USER
#    IS_UPDATES
#    IS_HOLDBACK
#    IS_SECURITY
# PROJECT_NAME
# PROJECT_VERSION
# DIST
# REMOTE_REPO_HOST
# GERRIT_PATCHSET_REVISION

# GERRIT_CHANGE_STATUS
# CUSTOM_REPO_ID
# SIGKEYID
# LP_BUG
# REPO_REQUEST_PATH_PREFIX
# IS_DOWNGRADE
# DEFAULTCOMPSXML
# REPO_BASE_PATH
_sign_rpm() {
    # ``rpmsign`` is interactive command and couldn't be called in direct way,
    # so here used ``expect`` for entering passphrase
    # params:
    # $1 -> sigkeyid
    # $2 -> binary to resign
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

    # fixme: this check is performed for rpm, but missed in deb
    [ $(ls -1 ${TMP_DIR}/ | wc -l) -eq 0 ] && error "Can't download packages"


    # Initialization of repository
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
    for repo_path in "${RPM_OS_REPO_PATH}"       \
                     "${RPM_PROPOSED_REPO_PATH}" \
                     "${RPM_UPDATES_REPO_PATH}"  \
                     "${RPM_SECURITY_REPO_PATH}" \
                     "${RPM_HOLDBACK_REPO_PATH}" ; do

        local _full_repo_path="${LOCAL_REPO_BASE_PATH}/${repo_path}"

        if [ ! -d "${_full_repo_path}" ] ; then

            # fixme: is it ok to wrap with "" ?
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

    # Fill in all the defaults
    # when some parameters are not given then fallback to "main" path
    # --------------------------------------------------

    [ -z "${RPM_UPDATES_REPO_PATH}" ] && RPM_UPDATES_REPO_PATH="${RPM_OS_REPO_PATH}"
    [ -z "${RPM_PROPOSED_REPO_PATH}" ] && RPM_PROPOSED_REPO_PATH="${RPM_OS_REPO_PATH}"
    [ -z "${RPM_SECURITY_REPO_PATH}" ] && RPM_SECURITY_REPO_PATH="${RPM_OS_REPO_PATH}"
    [ -z "${RPM_HOLDBACK_REPO_PATH}" ] && RPM_HOLDBACK_REPO_PATH="${RPM_OS_REPO_PATH}"

    RPM_REPO_PATH=${RPM_OS_REPO_PATH}
    [ "${IS_UPDATES}" == 'true' ] && RPM_REPO_PATH="${RPM_PROPOSED_REPO_PATH}"
    [ "${IS_HOLDBACK}" == 'true' ] && RPM_REPO_PATH="${RPM_HOLDBACK_REPO_PATH}"
    [ "${IS_SECURITY}" == 'true' ] && RPM_REPO_PATH="${RPM_SECURITY_REPO_PATH}"

    local LOCAL_REPO_PATH="${LOCAL_REPO_BASE_PATH}/${RPM_REPO_PATH}"


    # Filling of repository with new files
    # ==================================================

    # Aggregate list of files for further processing
    # --------------------------------------------------

    local BINRPMLIST=""
    local BINSRCLIST=""
    local BINSRCNAMES=""
    local BINRPMNAMES=""

    for binary in ${TMP_DIR}/* ; do
        if [ "${binary:(-7)}" == "src.rpm" ] ; then
            BINSRCLIST="${binary}"
            BINSRCNAMES="${binary##*/}"
        elif [ "${binary##*.}" == "rpm" ]; then
            BINRPMLIST="${BINRPMLIST} ${binary}"
            BINRPMNAMES="${BINRPMNAMES} ${binary##*/}"
        fi
    done

    BINNAMES="${BINSRCNAMES} ${BINRPMNAMES}"
    local PACKAGENAMES=""

    # Get existing srpm filename
    local SRPM_NAME="$(                                 \
        rpm -qp                                         \
            --queryformat "%{NAME}" ${BINSRCLIST}       \
    )"

    local _repoid_source="$(mktemp -u XXXXXXXX)"

    local OLD_SRPM_FILE="$(                             \
        repoquery --repofrompath=${_repoid_source},file://${LOCAL_REPO_PATH}/Source/ \
                  --repoid=${_repoid_source}            \
                  --archlist=src                        \
                  --location ${SRPM_NAME}               \
    )"

    local OLD_SRPM_FILE="${OLD_SRPM_FILE##*/}"

    # Get existing rpm files
    local repoquerysrpm_py="${SCRIPT_DIR}/repoquerysrpm.py"
    local OLD_RPM_FILES="$(                             \
        python ${repoquerysrpm_py}                      \
               --srpm=${OLD_SRPM_FILE}                  \
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
        for binary in ${BINRPMLIST} \
                      ${BINSRCLIST} ; do

            local PACKAGEFOLDER=

            if [ "${binary:(-7)}" == "src.rpm" ] ; then
                PACKAGEFOLDER="Source/SPackages"
            else
                PACKAGEFOLDER="x86_64/Packages"
            fi

            # Get package info
            local NEW_BINDATA="$(                       \
                rpm -qp                                 \
                    --queryformat "%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{SHA1HEADER}\n" \
                    ${binary}                           \
                    2>/dev/null                         \
            )"

            local _arr=($(echo "${NEW_BINDATA}"))
            unset NEW_BINDATA

            # splitting result into variables:
            local NEW_BINEPOCH="${_arr[1]}"
            local BINNAME="${_arr[2]}"
            local NEW_BINVERSION="${_arr[3]}"
            local NEW_BINRELEASE="${_arr[4]}"
            local NEW_BINSHA="${_arr[5]}"

            if [ "${NEW_BINEPOCH}" == "(none)" ] ; then
                NEW_BINEPOCH='0'
            fi

            if [ "${binary:(-7)}" != "src.rpm" ] ; then
                # append src.rpm packages to list
                local PACKAGENAMES="${PACKAGENAMES} ${BINNAME}"
            fi

            # OLD_BINDATA format pkg-name-epoch:version-release.arch (NEVRA)

            local _repoid_os="$(mktemp -u XXXXXXXX)"
            local _repoid_updates="$(mktemp -u XXXXXXXX)"
            local _repoid_proposed="$(mktemp -u XXXXXXXX)"
            local _repoid_holdback="$(mktemp -u XXXXXXXX)"
            local _repoid_security="$(mktemp -u XXXXXXXX)"

            local _additional_param=""
            if [ "${binary:(-7)}" == "src.rpm" ] ; then
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
            #

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
                # - package found and parsed:
                #   python-oslo-messaging-2.5.0-4.el7~mos16.git.196de7f.54be4a8.noarch

                local _pattern="${BINNAME}-${OLD_BINVERSION}-${OLD_BINRELEASE}.${OLD_BINARCH}*"

                find ${LOCAL_REPO_PATH}                 \
                     -name "${_pattern}"                \
                     -exec rm -f {} \;
                unset OLD_BINVERSION
            fi

            # Compare versions of new and existring packages

            local SKIPPACKAGE="no"

            if [ ! -z "${OLD_BINVERSION}" ] ; then

                # Comparing versions before including package to the repo
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

                local _old_pkg="${BINNAME}-${OLD_BINEPOCH}:${OLD_BINVERSION}-${OLD_BINRELEASE}"

                case "${CMPVER}" in
                    1)

                        error "Can't publish ${binary#*/}. Existing ${_old_pkg} has newer version"
                    ;;

                    0)  # Check sha for identical package names
                        OLD_RPMFILE=$(${repoquery_cmd} --location ${BINNAME})
                        OLD_BINSHA=$(rpm -qp --queryformat "%{SHA1HEADER}" ${OLD_RPMFILE})
                        if [ "${NEW_BINSHA}" == "${OLD_BINSHA}" ]; then
                            SKIPPACKAGE="yes"
                            info "Skipping including of ${binary}. Existing ${_old_pkg} has the same version and checksum"
                        else
                            error "Can't publish ${binary#*/}. Existing ${_old_pkg} has the same version but different checksum"
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
                _sign_rpm "${SIGKEYID}" "${binary}"

                if [ $? -ne 0 ] ; then
                    error "Something went wrong. Can't sign package ${binary#*/}"
                fi
            fi

            # fixme: why did we signed package if we don't want to include it into repo?

            if [ "${SKIPPACKAGE}" == "no" ] ; then
                cp "${binary}" "${LOCAL_REPO_PATH}/${PACKAGEFOLDER}"
            fi

        done

        # Remove old packages
        # ----------------------------------------------

        for file in ${OLD_SRPM_FILE} \
                    ${OLD_RPM_FILES} ; do

            # note: construction below means "if file not in BINNAMES"
            if [ "${BINNAMES}" == "${BINNAMES/$file/}" ] ; then
                find "${LOCAL_REPO_PATH}"               \
                     -type f                            \
                     -name ${file}                      \
                     -exec rm {} \;                     \
                     2>/dev/null
            fi

        done

        # Keep only latest packades

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
        sync-repo "${LOCAL_REPO_PATH}/" "${RPM_REPO_PATH}" "${REPO_REQUEST_PATH_PREFIX}" "${REQUEST_NUM}" "${LP_BUG}"

    job_lock ${LOCAL_REPO_PATH}.lock unset


    # Filling report file and export results
    # ==================================================


    local RPM_VERSION="${NEW_BINEPOCH}:${NEW_BINVERSION}-${NEW_BINRELEASE}"
    local RPM_REPO_URL="http://${REMOTE_REPO_HOST}/${URL_PREFIX}${RPM_REPO_PATH}/x86_64"
    local RPM_BINARIES="$(                              \
        echo ${PACKAGENAMES}                            \
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
