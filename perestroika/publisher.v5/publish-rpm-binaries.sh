#!/bin/bash -ex

SCRIPT_DIR=$(dirname $(readlink -e $0))

[ -f ".publisher-defaults-rpm" ] && source .publisher-defaults-rpm
source "${SCRIPT_DIR}/functions/publish-functions.sh"
source "${SCRIPT_DIR}/functions/locking.sh"

[ -z "${DEFAULTCOMPSXML}" ] && DEFAULTCOMPSXML=http://mirror.fuel-infra.org/fwm/6.0/centos/os/x86_64/comps.xml


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
# NEWBINEPOCH ?
# GERRIT_PATCHSET_REVISION

# GERRIT_CHANGE_STATUS
# CUSTOM_REPO_ID
# SIGKEYID
# LP_BUG
# REPO_REQUEST_PATH_PREFIX

main() {

    # Preparations
    # ==================================================

    # ???
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

    [ -d "${TMP_DIR}" ] && rm -rf "${TMP_DIR}"
    mkdir -p "${TMP_DIR}"


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


    # fixme: refactor
    local URL_PREFIX=""
    if [ "${GERRIT_CHANGE_STATUS}" == "NEW" ] ; then
        REPO_BASE_PATH=${REPO_BASE_PATH}/${REPO_REQUEST_PATH_PREFIX}
        URL_PREFIX=${REPO_REQUEST_PATH_PREFIX}
        if [ -n "${LP_BUG}" ] ; then
            REPO_BASE_PATH=${REPO_BASE_PATH}${LP_BUG}
            URL_PREFIX=${URL_PREFIX}${LP_BUG}/
        else
            REPO_BASE_PATH=${REPO_BASE_PATH}${REQUEST_NUM}
            URL_PREFIX=${URL_PREFIX}${REQUEST_NUM}/
        fi
    fi

    # Create all repositories
    for repo_path in "${RPM_OS_REPO_PATH}"       \
                     "${RPM_PROPOSED_REPO_PATH}" \
                     "${RPM_UPDATES_REPO_PATH}"  \
                     "${RPM_SECURITY_REPO_PATH}" \
                     "${RPM_HOLDBACK_REPO_PATH}" ; do

        local LOCAL_REPO_PATH="${REPO_BASE_PATH}/${repo_path}"

        if [ ! -d "${LOCAL_REPO_PATH}" ] ; then

            # fixme: is it possible to wrap with "" ?
            mkdir -p ${LOCAL_REPO_PATH}/{x86_64/Packages,Source/SPackages,x86_64/repodata}

            job_lock "${LOCAL_REPO_PATH}.lock" wait 3600

                createrepo --pretty \
                           --database \
                           --update \
                           -o ${LOCAL_REPO_PATH}/x86_64/ ${LOCAL_REPO_PATH}/x86_64

                createrepo --pretty \
                           --database \
                           --update \
                           -o ${LOCAL_REPO_PATH}/Source/ ${LOCAL_REPO_PATH}/Source

            job_lock "${LOCAL_REPO_PATH}.lock" unset
        fi
    done

    [ -z "${RPM_UPDATES_REPO_PATH}" ] && RPM_UPDATES_REPO_PATH=${RPM_OS_REPO_PATH}
    [ -z "${RPM_PROPOSED_REPO_PATH}" ] && RPM_PROPOSED_REPO_PATH=${RPM_OS_REPO_PATH}
    [ -z "${RPM_SECURITY_REPO_PATH}" ] && RPM_SECURITY_REPO_PATH=${RPM_OS_REPO_PATH}
    [ -z "${RPM_HOLDBACK_REPO_PATH}" ] && RPM_HOLDBACK_REPO_PATH=${RPM_OS_REPO_PATH}

    RPM_REPO_PATH=${RPM_OS_REPO_PATH}
    [ "${IS_UPDATES}" == 'true' ] && RPM_REPO_PATH=${RPM_PROPOSED_REPO_PATH}
    [ "${IS_HOLDBACK}" == 'true' ] && RPM_REPO_PATH=${RPM_HOLDBACK_REPO_PATH}
    [ "${IS_SECURITY}" == 'true' ] && RPM_REPO_PATH=${RPM_SECURITY_REPO_PATH}

    local LOCAL_REPO_PATH=${REPO_BASE_PATH}/${RPM_REPO_PATH}


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
    local SRPM_NAME="$(                         \
        rpm -qp                                 \
        --queryformat "%{NAME}" ${BINSRCLIST}   \
    )"
    local _repoid_source="$(mktemp -u XXXXXXXX)"

    local EXIST_SRPM_FILE="$(                   \
        repoquery --repofrompath=${_repoid_source},file://${LOCAL_REPO_PATH}/Source/ \
                  --repoid=${_repoid_source}    \
                  --archlist=src                \
                  --location ${SRPM_NAME}       \
    )"

    local EXIST_SRPM_FILE="${EXIST_SRPM_FILE##*/}"

    # Get existing rpm files
    local repoquerysrpm_py="${SCRIPT_DIR}/repoquerysrpm.py"
    local EXIST_RPM_FILES="$(\
        python ${repoquerysrpm_py}              \
               --srpm=${EXIST_SRPM_FILE}        \
               --path=${LOCAL_REPO_PATH}/x86_64/    \
        | awk -F'/' '{print $NF}'               \
    )"

    # Cleanup `repoquery` data
    find /var/tmp/yum-${USER}-*                 \
         -type d                                \
         -name ${_repoid_source}                \
         -exec rm -rf {} \; 2>/dev/null         \
    || true

    job_lock ${LOCAL_REPO_PATH}.lock wait 3600
    # Sign and publish binaries
    for binary in ${BINRPMLIST} \
                  ${BINSRCLIST} ; do

        local PACKAGEFOLDER="x86_64/Packages"
        if [ "${binary:(-7)}" == "src.rpm" ] ; then
            PACKAGEFOLDER="Source/SPackages"
        fi

        # Get package info
        local NEWBINDATA="$(                    \
            rpm -qp                             \
                --queryformat "%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{SHA1HEADER}\n" \
                ${binary}                       \
                2>/dev/null                     \
        )"

        local NEWBINEPOCH="$(                   \
            echo ${NEWBINDATA}                  \
            | cut -d' ' -f1                     \
        )"

        if [ "${NEWBINEPOCH}" == "(none)" ] ; then
            NEWBINEPOCH='0'
        fi
        local BINNAME=$(echo ${NEWBINDATA} | cut -d' ' -f2)
        [ "${binary:(-7)}" != "src.rpm" ] && local PACKAGENAMES="${PACKAGENAMES} ${BINNAME}"
        local NEWBINVERSION=$(echo ${NEWBINDATA} | cut -d' ' -f3)
        local NEWBINRELEASE=$(echo ${NEWBINDATA} | cut -d' ' -f4)
        local NEWBINSHA=$(echo ${NEWBINDATA} | cut -d' ' -f5)
        # EXISTBINDATA format pkg-name-epoch:version-release.arch (NEVRA)
        local _repoid_os=$(mktemp -u XXXXXXXX)
        local _repoid_updates=$(mktemp -u XXXXXXXX)
        local _repoid_proposed=$(mktemp -u XXXXXXXX)
        local _repoid_holdback=$(mktemp -u XXXXXXXX)
        local _repoid_security=$(mktemp -u XXXXXXXX)

        local repoquery_cmd="repoquery --repofrompath=${_repoid_os},file://${REPO_BASE_PATH}/${RPM_OS_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_os}"
        local repoquery_cmd="${repoquery_cmd} --repofrompath=${_repoid_updates},file://${REPO_BASE_PATH}/${RPM_UPDATES_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_updates}"
        local repoquery_cmd="${repoquery_cmd} --repofrompath=${_repoid_proposed},file://${REPO_BASE_PATH}/${RPM_PROPOSED_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_proposed}"
        local repoquery_cmd="${repoquery_cmd} --repofrompath=${_repoid_holdback},file://${REPO_BASE_PATH}/${RPM_HOLDBACK_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_holdback}"
        local repoquery_cmd="${repoquery_cmd} --repofrompath=${_repoid_security},file://${REPO_BASE_PATH}/${RPM_SECURITY_REPO_PATH}/${PACKAGEFOLDER%/*} --repoid=${_repoid_security}"
        [ "${binary:(-7)}" == "src.rpm" ] && repoquery_cmd="${repoquery_cmd} --archlist=src"
        local EXISTBINDATA=$(${repoquery_cmd} ${BINNAME} 2>/dev/null)

        # Cleanup `repoquery` data
        for _repoid in ${_repoid_os} \
                        ${_repoid_updates} \
                        ${_repoid_proposed} \
                        ${_repoid_holdback} \
                        ${_repoid_security} ; do

            find /var/tmp/yum-${USER}-* -type d -name $_repoid -exec rm -rf {} \; 2>/dev/null || :
        done

        # Get arch
        local EXISTBINARCH=${EXISTBINDATA##*.}
        # Skip arch
        local EXISTBINDATA=${EXISTBINDATA%.*}
        # Get epoch
        local EXISTBINEPOCH=$(echo ${EXISTBINDATA} | cut -d':' -f1 | awk -F'-' '{print $NF}')
        # Skip "pkg-name-epoch:"
        local EXISTBINDATA=${EXISTBINDATA#*:}
        # Get version
        local EXISTBINVERSION=${EXISTBINDATA%%-*}
        # Get release
        local EXISTBINRELEASE=${EXISTBINDATA#*-}

        ## FixMe: Improve packages removing
        # Remove existing packages from repo (for new change requests and downgrades)
        if [ "${GERRIT_CHANGE_STATUS}" == "NEW" -o "$IS_DOWNGRADE" == "true" ] ;  then
            find ${LOCAL_REPO_PATH} \
                 -name "${BINNAME}-${EXISTBINVERSION}-${EXISTBINRELEASE}.${EXISTBINARCH}*" \
                 -exec rm -f {} \;
            # fixme:         ^^-^^----- ???
            unset EXISTBINVERSION
        fi
        # Compare versions of new and existring packages
        local SKIPPACKAGE=0
        if [ ! -z "${EXISTBINVERSION}" ] ; then
        ############################################################
        ## Comparing versions before including package to the repo
        ##

        # fixme: how to use features of tempfiles from functions?
        echo                                     > "${SCRIPT_DIR}/tmp"
        echo "from rpmUtils import miscutils"   >> "${SCRIPT_DIR}/tmp"
        echo "print miscutils.compareEVR( \
                    (\"${EXISTBINEPOCH}\", \"${EXISTBINVERSION}\", \"${EXISTBINRELEASE}\" ),
			        (\"${NEWBINEPOCH}\",   \"${NEWBINVERSION}\",   \"${NEWBINRELEASE}\"   )) " \
			                                    >> "${SCRIPT_DIR}/tmp"
        CMPVER=$(python ${SCRIPT_DIR}/tmp)

        # Results:
        #  1 - EXISTBIN is newer than NEWBIN
        #  0 - EXISTBIN and NEWBIN have the same version
        # -1 - EXISTBIN is older than NEWBIN

        case "${CMPVER}" in
            1)
                error "Can't publish ${binary#*/}. Existing ${BINNAME}-${EXISTBINEPOCH}:${EXISTBINVERSION}-${EXISTBINRELEASE} has newer version"
            ;;

            0)  # Check sha for identical package names
                EXISTRPMFILE=$(${repoquery_cmd} --location ${BINNAME})
                EXISTBINSHA=$(rpm -qp --queryformat "%{SHA1HEADER}" ${EXISTRPMFILE})
                if [ "${NEWBINSHA}" == "${EXISTBINSHA}" ]; then
                    SKIPPACKAGE=1
                    info "Skipping including of ${binary}. Existing ${BINNAME}-${EXISTBINEPOCH}:${EXISTBINVERSION}-${EXISTBINRELEASE} has the same version and checksum"
                else
                    error "Can't publish ${binary#*/}. Existing ${BINNAME}-${EXISTBINEPOCH}:${EXISTBINVERSION}-${EXISTBINRELEASE} has the same version but different checksum"
                fi
            ;;

            *)
                true
            ;;
        esac
        ##
        ############################################################
    fi
    ############
    ## Signing
    ##
    if [ -n "${SIGKEYID}" ] ; then
        # rpmsign requires pass phrase. use `expect` to skip it

        LANG=C expect <<EOL
spawn rpmsign --define "%__gpg_check_password_cmd /bin/true" --define "%_signature gpg" --define "%_gpg_name ${SIGKEYID}" --resign ${binary}
expect -exact "Enter pass phrase:"
send -- "Doesn't matter\r"
expect eof
lassign [wait] pid spawnid os_error_flag value
puts "exit status: \$value"
exit \$value
EOL
        [ $? -ne 0 ] && error "Something went wrong. Can't sign package ${binary#*/}"
      fi
      ##
      ###########
      [ "${SKIPPACKAGE}" == "0" ] && cp ${binary} ${LOCAL_REPO_PATH}/${PACKAGEFOLDER}
  done

    # Remove old packages
    for file in ${EXIST_SRPM_FILE} \
                ${EXIST_RPM_FILES} ; do
        if [ "${BINNAMES}" == "${BINNAMES/$file/}" ] ; then
            find ${LOCAL_REPO_PATH} -type f -name ${file} -exec rm {} \; 2>/dev/null
        fi
    done

    rm -f $(repomanage --keep=1 --old ${LOCAL_REPO_PATH}/x86_64)
    rm -f $(repomanage --keep=1 --old ${LOCAL_REPO_PATH}/Source)

    # Update and sign repository metadata

    if [ ! -e ${LOCAL_REPO_PATH}/comps.xml ] ; then
        wget ${DEFAULTCOMPSXML} -O ${LOCAL_REPO_PATH}/comps.xml
    fi

    # fixme: looks like ${LOCAL_REPO_PATH}/x86_64 & ${LOCAL_REPO_PATH}/Source are duplicated in params.
    createrepo --pretty                 \
               --database               \
               --update                 \
               -g ${LOCAL_REPO_PATH}/comps.xml \
               -o ${LOCAL_REPO_PATH}/x86_64/ ${LOCAL_REPO_PATH}/x86_64

    createrepo --pretty                 \
               --database               \
               --update                 \
               -o ${LOCAL_REPO_PATH}/Source/ ${LOCAL_REPO_PATH}/Source

    if [ -n "${SIGKEYID}" ] ; then
        rm -f ${LOCAL_REPO_PATH}/x86_64/repodata/repomd.xml.asc
        rm -f ${LOCAL_REPO_PATH}/Source/repodata/repomd.xml.asc
        gpg --armor --local-user ${SIGKEYID} --detach-sign ${LOCAL_REPO_PATH}/x86_64/repodata/repomd.xml
        gpg --armor --local-user ${SIGKEYID} --detach-sign ${LOCAL_REPO_PATH}/Source/repodata/repomd.xml

        if [ -f "RPM-GPG-KEY" ] ; then
            cp RPM-GPG-KEY ${LOCAL_REPO_PATH}/RPM-GPG-KEY-${PROJECT_NAME}${PROJECT_VERSION}
        fi
    fi

    # Sync repo to remote host
    sync-repo ${LOCAL_REPO_PATH}/ ${RPM_REPO_PATH} ${REPO_REQUEST_PATH_PREFIX} ${REQUEST_NUM} ${LP_BUG}
    job_lock ${LOCAL_REPO_PATH}.lock unset

    rm -f ${WRK_DIR}/rpm.publish.setenvfile

    cat > ${WRK_DIR}/rpm.publish.setenvfile <<-EOF
	RPM_PUBLISH_SUCCEEDED=true
	RPM_DISTRO=${DIST}
	RPM_VERSION=${NEWBINEPOCH}:${NEWBINVERSION}-${NEWBINRELEASE}
	RPM_REPO_URL=http://${REMOTE_REPO_HOST}/${URL_PREFIX}${RPM_REPO_PATH}/x86_64
	RPM_BINARIES=$(echo ${PACKAGENAMES} | sed 's|^ ||; s| |,|g')
	RPM_CHANGE_REVISION=${GERRIT_PATCHSET_REVISION}
	LP_BUG=${LP_BUG}
EOF
}

main "$@"

exit 0
