#!/bin/bash -ex

SCRIPT_DIR="$(dirname $(readlink -e $0))"

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
        gpg --export -a ${SIGKEYID} > RPM-GPG-KEY
        if [ $(rpm -qa | grep gpg-pubkey | grep -ci ${SIGKEYID}) -eq 0 ]; then
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

    rsync -avPzt -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${SSH_OPTS}" \
        ${SSH_USER}${BUILD_HOST}:${PKG_PATH}/ ${TMP_DIR}/ || error "Can't download packages"

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
        REQUEST_NUM=${CUSTOM_REPO_ID}
    fi

    # Configuring paths and namespaces:
    # - only newly created patchsets have prefixes
    # - if LP_BUG is given then it replaces REQUEST_NUM ("Grouping" feature)
    # ---------------------------------------------------

    local URL_PREFIX=''

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
    # ---------------------------------------------------


    for repo_path in ${RPM_OS_REPO_PATH} ${RPM_PROPOSED_REPO_PATH} ${RPM_UPDATES_REPO_PATH} ${RPM_SECURITY_REPO_PATH} ${RPM_HOLDBACK_REPO_PATH} ; do
        local LOCAL_REPO_PATH=${REPO_BASE_PATH}/${repo_path}
        if [ ! -d "${LOCAL_REPO_PATH}" ] ; then
            mkdir -p ${LOCAL_REPO_PATH}/{x86_64/Packages,Source/SPackages,x86_64/repodata}
            job_lock ${LOCAL_REPO_PATH}.lock wait 3600
                createrepo --pretty --database --update -o ${LOCAL_REPO_PATH}/x86_64/ ${LOCAL_REPO_PATH}/x86_64
                createrepo --pretty --database --update -o ${LOCAL_REPO_PATH}/Source/ ${LOCAL_REPO_PATH}/Source
            job_lock ${LOCAL_REPO_PATH}.lock unset
        fi
    done


    # Defining repository name
    # Here we determine where to put new packages
    # ==================================================

    # Fill in all the defaults
    # when some parameters are not given then fallback to "main" path
    # --------------------------------------------------

    [ -z "${RPM_UPDATES_REPO_PATH}" ] && RPM_UPDATES_REPO_PATH=${RPM_OS_REPO_PATH}
    [ -z "${RPM_PROPOSED_REPO_PATH}" ] && RPM_PROPOSED_REPO_PATH=${RPM_OS_REPO_PATH}
    [ -z "${RPM_SECURITY_REPO_PATH}" ] && RPM_SECURITY_REPO_PATH=${RPM_OS_REPO_PATH}
    [ -z "${RPM_HOLDBACK_REPO_PATH}" ] && RPM_HOLDBACK_REPO_PATH=${RPM_OS_REPO_PATH}

    RPM_REPO_PATH=${RPM_OS_REPO_PATH}


    # Processing different kinds of input directives "IS_XXX"
    # --------------------------------------------------


    # Updates workflow:
    # all built packages should be put into proposed repository
    # after tests and acceptance they are published to updates by other tools
    # --------------------------------------------------


    [ "${IS_UPDATES}" == 'true' ] && RPM_REPO_PATH=${RPM_PROPOSED_REPO_PATH}

    # Holdback workflow:
    # all built packages should be put into holdback repository
    # this wotkflow should be used in esceeptional cases
    # --------------------------------------------------

    [ "${IS_HOLDBACK}" == 'true' ] && RPM_REPO_PATH=${RPM_HOLDBACK_REPO_PATH}

    # Security workflow:
    # all built packages should be put into security repository
    # this is short-circuit for delivering security updates beside long updates workflow
    # --------------------------------------------------

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

    # Binaries to compare
    BINNAMES="${BINSRCNAMES} ${BINRPMNAMES}"
    local PACKAGENAMES=""

    # Get existing srpm filename
    local SRPM_NAME=$(rpm -qp --queryformat "%{NAME}" ${BINSRCLIST})
    local _repoid_source=$(mktemp -u XXXXXXXX)
    local repoquery_opts="--repofrompath=${_repoid_source},file://${LOCAL_REPO_PATH}/Source/ --repoid=${_repoid_source}"
    local EXIST_SRPM_FILE=$(repoquery ${repoquery_opts} --archlist=src --location ${SRPM_NAME})
    local EXIST_SRPM_FILE=${EXIST_SRPM_FILE##*/}
    # Get existing rpm files
    local repoquerysrpm_py="$(dirname $(readlink -e $0))/repoquerysrpm.py"
    local EXIST_RPM_FILES=$(python ${repoquerysrpm_py} --srpm=${EXIST_SRPM_FILE} --path=${LOCAL_REPO_PATH}/x86_64/ | awk -F'/' '{print $NF}')
    # Cleanup `repoquery` data
    find /var/tmp/yum-${USER}-* -type d -name $_repoid_source -exec rm -rf {} \; 2>/dev/null || :

    job_lock ${LOCAL_REPO_PATH}.lock wait 3600
        # Sign and publish binaries
        for binary in ${BINRPMLIST} ${BINSRCLIST} ; do
            local PACKAGEFOLDER=x86_64/Packages
            [ "${binary:(-7)}" == "src.rpm" ] && PACKAGEFOLDER=Source/SPackages

            # Get package info
            local NEWBINDATA=$(rpm -qp --queryformat "%{EPOCH} %{NAME} %{VERSION} %{RELEASE} %{SHA1HEADER}\n" ${binary} 2>/dev/null)

            # splitting result into variables:
            local NEWBINEPOCH=$(echo ${NEWBINDATA} | cut -d' ' -f1)
            [ "${NEWBINEPOCH}" == "(none)" ] && NEWBINEPOCH='0'
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
            for _repoid in $_repoid_os $_repoid_updates $_repoid_proposed $_repoid_holdback $_repoid_security ; do
                find /var/tmp/yum-${USER}-* -type d -name $_repoid -exec rm -rf {} \; 2>/dev/null || :
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
                find ${LOCAL_REPO_PATH} -name "${BINNAME}-${EXISTBINVERSION}-${EXISTBINRELEASE}.${EXISTBINARCH}*" \
                    -exec rm -f {} \;
                unset EXISTBINVERSION
            fi
            # Compare versions of new and existring packages
            local SKIPPACKAGE=0
            if [ ! -z "${EXISTBINVERSION}" ] ; then

                # Comparing versions before including package to the repo
                # When we have deal with the same package, we could skip it and don't publish
                # --------------------------------------

                local CMPVER="$(                        \
                    A_EPOCH="${EXISTBINEPOCH}"          \
                    A_VERSION="${EXISTBINVERSION}"      \
                    A_RELEASE="${EXISTBINRELEASE}"      \
                    B_EPOCH="${NEWBINEPOCH}"            \
                    B_VERSION="${NEWBINVERSION}"        \
                    B_RELEASE="${NEWBINRELEASE}"        \
                    python "${SCRIPT_DIR}/cmp_evr.py"   \
                )"

                # Results:
                #  1 - EXISTBIN is newer than NEWBIN
                #  0 - EXISTBIN and NEWBIN have the same version
                # -1 - EXISTBIN is older than NEWBIN
                case ${CMPVER} in
                   1) error "Can't publish ${binary#*/}. Existing ${BINNAME}-${EXISTBINEPOCH}:${EXISTBINVERSION}-${EXISTBINRELEASE} has newer version" ;;
                   0) # Check sha for identical package names
                      EXISTRPMFILE=$(${repoquery_cmd} --location ${BINNAME})
                      EXISTBINSHA=$(rpm -qp --queryformat "%{SHA1HEADER}" ${EXISTRPMFILE})
                      if [ "${NEWBINSHA}" == "${EXISTBINSHA}" ]; then
                          SKIPPACKAGE=1
                          echo "Skipping including of ${binary}. Existing ${BINNAME}-${EXISTBINEPOCH}:${EXISTBINVERSION}-${EXISTBINRELEASE} has the same version and checksum"
                      else
                          error "Can't publish ${binary#*/}. Existing ${BINNAME}-${EXISTBINEPOCH}:${EXISTBINVERSION}-${EXISTBINRELEASE} has the same version but different checksum"
                      fi
                      ;;
                   *) : ;;
                esac

            fi

            # Signing
            # ------------------------------------------

            if [ -n "${SIGKEYID}" ] ; then
                _sign_rpm "${SIGKEYID}" "${binary}"
                [ $? -ne 0 ] && error "Something went wrong. Can't sign package ${binary#*/}"
            fi

            # fixme: why did we signed package if we don't want to include it into repo?

            [ "${SKIPPACKAGE}" == "0" ] && cp ${binary} ${LOCAL_REPO_PATH}/${PACKAGEFOLDER}
        done

        # Cleanup files from previous version
        # When packages are replaced, there could stay some artifacts
        # from previously published version, so it's required to clean them.
        #
        # ----------------------------------------------

        for file in ${EXIST_SRPM_FILE} ${EXIST_RPM_FILES} ; do
          [ "${BINNAMES}" == "${BINNAMES/$file/}" ] \
              && find ${LOCAL_REPO_PATH} -type f -name ${file} -exec rm {} \; 2>/dev/null
        done

        # Keep only latest packages

        rm -f $(repomanage --keep=1 --old ${LOCAL_REPO_PATH}/x86_64)
        rm -f $(repomanage --keep=1 --old ${LOCAL_REPO_PATH}/Source)

        # Update and sign repository metadata
        # ----------------------------------------------

        [ ! -e ${LOCAL_REPO_PATH}/comps.xml ] && wget ${DEFAULTCOMPSXML} -O ${LOCAL_REPO_PATH}/comps.xml
        createrepo --pretty --database --update -g ${LOCAL_REPO_PATH}/comps.xml -o ${LOCAL_REPO_PATH}/x86_64/ ${LOCAL_REPO_PATH}/x86_64
        createrepo --pretty --database --update -o ${LOCAL_REPO_PATH}/Source/ ${LOCAL_REPO_PATH}/Source
        if [ -n "${SIGKEYID}" ] ; then
            rm -f ${LOCAL_REPO_PATH}/x86_64/repodata/repomd.xml.asc
            rm -f ${LOCAL_REPO_PATH}/Source/repodata/repomd.xml.asc
            gpg --armor --local-user ${SIGKEYID} --detach-sign ${LOCAL_REPO_PATH}/x86_64/repodata/repomd.xml
            gpg --armor --local-user ${SIGKEYID} --detach-sign ${LOCAL_REPO_PATH}/Source/repodata/repomd.xml
            [ -f "RPM-GPG-KEY" ] && cp RPM-GPG-KEY ${LOCAL_REPO_PATH}/RPM-GPG-KEY-${PROJECT_NAME}${PROJECT_VERSION}
        fi

        # Sync repo to remote host
        sync-repo ${LOCAL_REPO_PATH}/ ${RPM_REPO_PATH} ${REPO_REQUEST_PATH_PREFIX} ${REQUEST_NUM} ${LP_BUG}
    job_lock ${LOCAL_REPO_PATH}.lock unset


    # Filling report file and export results
    # ==================================================


    local RPM_VERSION="${NEWBINEPOCH}:${NEWBINVERSION}-${NEWBINRELEASE}"
    local RPM_REPO_URL="http://${REMOTE_REPO_HOST}/${URL_PREFIX}${RPM_REPO_PATH}/x86_64"
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

main "$@"

exit 0
