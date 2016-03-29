#!/bin/bash -ex

SCRIPT_DIR="$(dirname $(readlink -e $0))"

[ -f ".publisher-defaults-deb" ] && source .publisher-defaults-deb
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
#
# Security-related parameters
# ------------------------------------------------------
# SIGKEYID           user used for signing release files
# PROJECT_NAME       project name used for look up key file
# PROJECT_VERSION    project name used for look up key file
#
#
# Repository paths and urls configuration
# repo path ::= "(1)/[(2)(3)]/(4)"
# repo url  ::= "http://(0)/[(2)(3)]/(4) (distribution) (component)"
# ------------------------------------------------------
# REPO_BASE_PATH            (1) first part of repo path
# REPO_REQUEST_PATH_PREFIX  (2) second part of repo path (optional)
# CUSTOM_REPO_ID            (3) third part - highest priority override (optional)
# *LP_BUG                   (3) third part - LP bug (optional)
# *REQUEST_NUM              (3) third part - used when no LP bug provided (optional)
# DEB_REPO_PATH             (4) fourth part of repo path
#
# REMOTE_REPO_HOST          (0) fqdn of server where to publish built packages
# ORIGIN                    origin
# PRODUCT_VERSION           version of product
# DIST                      Name of OS distributive (trusty, for ex.)
#
#
# Distributions naming
# It's possible to provide overrides which should be used
# as names for proposed, secutity, updates and holdback distributions
# DEB_DIST_NAME will be used if no overrides given
# ------------------------------------------------------
# DEB_DIST_NAME             name of "main" distributions repo (for ex. mos8.0)
# DEB_PROPOSED_DIST_NAME    name of "proposed" distributions repo (for ex. mos8.0-proposed) (optional)
# DEB_UPDATES_DIST_NAME     name of "updates" distributions repo (for ex. mos8.0-updates) (optional)
# DEB_SECURITY_DIST_NAME    name of "security" distributions repo (for ex. mos8.0-security) (optional)
# DEB_HOLDBACK_DIST_NAME    name of "holdback" distributions repo (for ex. mos8.0-holdback) (optional)
#
#
# Component parameters
# It's possible to provide overrides which should be used
# as names for proposed, secutity, updates and holdback components
# DEB_DIST_NAME will be used if no overrides given
# ------------------------------------------------------
# DEB_COMPONENT             name of "main" component (optional)
# DEB_PROPOSED_COMPONENT    name of "proposed" component (optional)
# DEB_UPDATES_COMPONENT     name of "updates" component (optional)
# DEB_SECURITY_COMPONENT    name of "security" component (optional)
# DEB_HOLDBACK_COMPONENT    name of "holdback" component (optional)
#
#
# Directives for using different kinds of workflows which
# define output repos/component name for packages
# (will be applied directive with highest priority)
# ------------------------------------------------------
# IS_UPDATES         p1. updates workflow -> publish to proposed repo
# IS_HOLDBACK        p2. holdback workflow -> publish to holdback repo (USE WITH CARE!)
# IS_SECURITY        p3. security workflow -> publish to security repo
# IS_RESTRICTED      force to set component name "restricted" (USE WITH CARE!)
# IS_DOWNGRADE       downgrade package: remove ONE previously published version of this package


main() {

    # Preparations
    # ==================================================

    # Check if it's possible to sign packages
    # --------------------------------------------------

    local SIGN_STRING=""
    check-gpg && SIGN_STRING="true"

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

    ## Resign source package
    ## FixMe: disabled for discussion: does it really need to sign
    #[ -n "${SIGN_STRING}" ] && \
    #    for _dscfile in $(find ${TMP_DIR} -name "*.dsc") ; do
    #        debsign -pgpg --re-sign -k${SIGKEYID} ${_dscfile}
    #    done


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

    # Configuring paths and namespaces:
    # - only newly created patchsets have prefixes
    # - if LP_BUG is given then it replaces REQUEST_NUM ("Grouping" feature)
    # ---------------------------------------------------


    local URL_PREFIX=""
    if [ "${GERRIT_CHANGE_STATUS}" = "NEW" ] ; then
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

    local LOCAL_REPO_PATH=${REPO_BASE_PATH}/${DEB_REPO_PATH}
    local DBDIR="+b/db"
    local CONFIGDIR="${LOCAL_REPO_PATH}/conf"
    local DISTDIR="${LOCAL_REPO_PATH}/public/dists/"
    local OUTDIR="+b/public/"

    if [ ! -d "${CONFIGDIR}" ] ; then
        mkdir -p "${CONFIGDIR}"

        job_lock "${CONFIGDIR}.lock" wait 3600

            for dist_name in "${DEB_DIST_NAME}"          \
                             "${DEB_PROPOSED_DIST_NAME}" \
                             "${DEB_UPDATES_DIST_NAME}"  \
                             "${DEB_SECURITY_DIST_NAME}" \
                             "${DEB_HOLDBACK_DIST_NAME}" ; do

                # Filling distributions configuretion file (this file is used by reprepro)
                # It's not cleaned at beginning, because publisher didn't clean
                # it in it's previous versions.
                # This behavior looks like a bug. But fixing it could result in
                # unexpected behavior and should be tested with care.
                # --------------------------------------

                echo "Origin: ${ORIGIN}"                  >> "${CONFIGDIR}/distributions"
                echo "Label: ${DEB_DIST_NAME}"            >> "${CONFIGDIR}/distributions"
                echo "Suite: ${dist_name}"                >> "${CONFIGDIR}/distributions"
                echo "Codename: ${dist_name}"             >> "${CONFIGDIR}/distributions"
                echo "Version: ${PRODUCT_VERSION}"        >> "${CONFIGDIR}/distributions"
                echo "Architectures: amd64 i386 source"   >> "${CONFIGDIR}/distributions"
                echo "Components: main restricted"        >> "${CONFIGDIR}/distributions"
                echo "UDebComponents: main restricted"    >> "${CONFIGDIR}/distributions"
                echo "Contents: . .gz .bz2"               >> "${CONFIGDIR}/distributions"
                echo ""                                   >> "${CONFIGDIR}/distributions"

                reprepro --basedir ${LOCAL_REPO_PATH} \
                         --dbdir ${DBDIR} \
                         --outdir ${OUTDIR} \
                         --distdir ${DISTDIR} \
                         --confdir ${CONFIGDIR} \
                         export ${dist_name}

                # Fix Codename field
                # This is done because reprepro is created for deb but used for ubuntu
                # it's ok, that codename is set as DEB_DIST_NAME and not as dist_name
                # --------------------------------------

                local release_file="${DISTDIR}/${dist_name}/Release"

                sed "s|^Codename:.*$|Codename: ${DEB_DIST_NAME}|" -i "${release_file}"

                rm -f "${release_file}.gpg"

                # Signing changed release file
                # --------------------------------------

                if [ -n "${SIGN_STRING}" ] ; then

                    gpg --sign                          \
                        --local-user "${SIGKEYID}"      \
                        -ba                             \
                        -o "${release_file}.gpg" "${release_file}"

                fi

            done

        job_lock "${CONFIGDIR}.lock" unset

    fi


    # Defining distribution name and component
    # Here we determine where to put new packages
    # ==================================================

    # Fill in all the defaults
    # when some parameters are not given then fallback to main distribution/component
    # --------------------------------------------------

    DEB_BASE_DIST_NAME=${DEB_DIST_NAME}

    [ -z "${DEB_UPDATES_DIST_NAME}" ] && DEB_UPDATES_DIST_NAME="${DEB_DIST_NAME}"
    [ -z "${DEB_PROPOSED_DIST_NAME}" ] && DEB_PROPOSED_DIST_NAME="${DEB_DIST_NAME}"
    [ -z "${DEB_SECURITY_DIST_NAME}" ] && DEB_SECURITY_DIST_NAME="${DEB_DIST_NAME}"
    [ -z "${DEB_HOLDBACK_DIST_NAME}" ] && DEB_HOLDBACK_DIST_NAME="${DEB_DIST_NAME}"

    [ -z "${DEB_UPDATES_COMPONENT}" ] && DEB_UPDATES_COMPONENT="${DEB_COMPONENT}"
    [ -z "${DEB_PROPOSED_COMPONENT}" ] && DEB_PROPOSED_COMPONENT="${DEB_COMPONENT}"
    [ -z "${DEB_SECURITY_COMPONENT}" ] && DEB_SECURITY_COMPONENT="${DEB_COMPONENT}"
    [ -z "${DEB_HOLDBACK_COMPONENT}" ] && DEB_HOLDBACK_COMPONENT="${DEB_COMPONENT}"

    # Processing different kinds of input directives "IS_XXX"
    # --------------------------------------------------


    # Updates workflow:
    # all built packages should be put into proposed distribution repository
    # after tests and acceptance they are published to updates by other tools
    # --------------------------------------------------

    if [ "${IS_UPDATES}" = 'true' ] ; then
        LOCAL_DEB_DIST_NAME="${DEB_PROPOSED_DIST_NAME}"
        LOCAL_DEB_COMPONENT="${DEB_PROPOSED_COMPONENT}"
    fi

    # Holdback workflow:
    # all built packages should be put into holdback distribution repository
    # this wotkflow should be used in esceeptional cases
    # --------------------------------------------------

    if [ "${IS_HOLDBACK}" = 'true' ] ; then
        LOCAL_DEB_DIST_NAME="${DEB_HOLDBACK_DIST_NAME}"
        LOCAL_DEB_COMPONENT="${DEB_HOLDBACK_COMPONENT}"
    fi

    # Security workflow:
    # all built packages should be put into security distribution repository
    # this is short-circuit for delivering security updates beside long updates workflow
    # --------------------------------------------------

    if [ "${IS_SECURITY}" = 'true' ] ; then
        LOCAL_DEB_DIST_NAME="${DEB_SECURITY_DIST_NAME}"
        LOCAL_DEB_COMPONENT="${DEB_SECURITY_COMPONENT}"
    fi

    if [ -z "${DEB_COMPONENT}" ] ; then
        DEB_COMPONENT="main"
    fi

    # Restricted components:
    # forcefully change component to restricted
    # --------------------------------------------------

    if [ "${IS_RESTRICTED}" = 'true' ] ; then
        LOCAL_DEB_COMPONENT="restricted"
    fi

    local LOCAL_REPO_PATH=${REPO_BASE_PATH}/${DEB_REPO_PATH}
    local CONFIGDIR="${LOCAL_REPO_PATH}/conf"
    local DBDIR="+b/db"
    local DISTDIR="${LOCAL_REPO_PATH}/public/dists/"
    local OUTDIR="${LOCAL_REPO_PATH}/public/"
    local REPREPRO_OPTS="--verbose --basedir ${LOCAL_REPO_PATH} --dbdir ${DBDIR} \
        --outdir ${OUTDIR} --distdir ${DISTDIR} --confdir ${CONFIGDIR}"
    local REPREPRO_COMP_OPTS="${REPREPRO_OPTS} --component ${DEB_COMPONENT}"

    # Filling of repository with new files
    # ==================================================

    # Aggregate list of files for further processing
    # --------------------------------------------------

    local BINDEBLIST=""
    local BINDEBNAMES=""
    local BINUDEBLIST=""
    local BINSRCLIST=""
    for binary in ${TMP_DIR}/* ; do
        case ${binary##*.} in
            deb)
                BINDEBLIST="${BINDEBLIST} ${binary}"
                BINDEBNAMES="${BINDEBNAMES} ${binary##*/}"
            ;;
            udeb)
                BINUDEBLIST="${BINUDEBLIST} ${binary}"
            ;;
            dsc)
                # note: we don't extend list of sources, because
                #       publisher doesn't support masspublishing of packages
                #       built from different sources

                BINSRCLIST="${binary}"
            ;;
        esac
    done

    job_lock "${CONFIGDIR}.lock" wait 3600

        # Get source name - this name represents sources from which package(s) was built
        # ----------------------------------------------

        local SRC_NAME="$(                              \
            awk '/^Source:/ {print $2}' ${BINSRCLIST}   \
        )"

        # Get queued version of package related to the SRC_NAME
        # because publisher doesn't support masspublishing,
        # it's ok, that we get one variable from list
        # ----------------------------------------------

        local NEW_VERSION="$(                           \
            awk '/^Version:/ {print $2}' ${BINSRCLIST}  \
            | head -n 1                                 \
        )"

        # Get currently published version of package related to the SRC_NAME
        # note: we hold only one version of each package
        # ----------------------------------------------

        local OLD_VERSION="$(                           \
            reprepro ${REPREPRO_OPTS}                   \
                     --list-format '${version}\n'       \
                     listfilter ${LOCAL_DEB_DIST_NAME} "Package (==${SRC_NAME})" \
            | sort -u                                   \
            | head -n 1                                 \
        )"

        [ "${OLD_VERSION}" == "" ] && OLD_VERSION=none

        # Remove existing packages for requests-on-review and downgrades
        # when there is previous version
        # ----------------------------------------------

        # TODO: Get rid of removing. Just increase version properly
        if [ "${GERRIT_CHANGE_STATUS}" = "NEW" -o "$IS_DOWNGRADE" == "true" ] ; then
            reprepro ${REPREPRO_OPTS} removesrc ${DEB_DIST_NAME} ${SRC_NAME} ${OLD_VERSION} || :
        fi

        # Collecting all binaries
        # ----------------------------------------------

        # Add .deb binaries
        if [ "${BINDEBLIST}" != "" ]; then

            reprepro ${REPREPRO_COMP_OPTS}              \
                     includedeb "${LOCAL_DEB_DIST_NAME}" ${BINDEBLIST} \
            || error "Can't include .deb packages"

        fi

        # Add .udeb binaries
        if [ "${BINUDEBLIST}" != "" ]; then

            reprepro ${REPREPRO_COMP_OPTS}              \
                     includeudeb "${LOCAL_DEB_DIST_NAME}" ${BINUDEBLIST} \
            || error "Can't include .udeb packages"

        fi

        # Replace sources
        # TODO: Get rid of replacing. Just increase version properly
        if [ "${BINSRCLIST}" != "" ]; then

            reprepro ${REPREPRO_COMP_OPTS}              \
                     --architecture source              \
                     remove ${LOCAL_DEB_DIST_NAME} ${SRC_NAME} \
            || true

            reprepro ${REPREPRO_COMP_OPTS}              \
                     includedsc ${LOCAL_DEB_DIST_NAME} ${BINSRCLIST} \
            || error "Can't include packages"

        fi

        # Cleanup files from previous version
        # When packages are replaced, there could stay some artifacts
        # from previously published version, so it's required to clean them.
        #
        # note: this step is done after adding new packages, and not before,
        #       because there is some logic inside reprepro which performs
        #       some useful checks
        #
        # note: looks like this case is useful for upgrades only, because
        #       in other cases everything is removed by first pass
        # ----------------------------------------------

        if [ "${OLD_VERSION}" != "${NEW_VERSION}" ] ; then

            reprepro ${REPREPRO_OPTS}                   \
                     removesrc "${DEB_DIST_NAME}" "${SRC_NAME}" "${OLD_VERSION}"
        fi

        # Fix Codename field
        # This is done because reprepro is created for deb but used for ubuntu
        # it's ok, that codename is set as DEB_DIST_NAME and not as dist_name
        # ----------------------------------------------

        local release_file="${DISTDIR}/${DEB_DIST_NAME}/Release"

        sed "s|^Codename:.*$|Codename: ${DEB_BASE_DIST_NAME}|" -i ${release_file}


        # Signing changed release file
        # fixme: why we do it in other way than in the beginning of the file?
        # ----------------------------------------------

        rm -f "${release_file}.gpg"
        local pub_key_file="${LOCAL_REPO_PATH}/public/archive-${PROJECT_NAME}${PROJECT_VERSION}.key"

        if [ -n "${SIGN_STRING}" ] ; then

            gpg --sign                                  \
                --local-user "${SIGKEYID}"              \
                -ba                                     \
                -o "${release_file}.gpg" "${release_file}"

            if [ ! -f "${pub_key_file}" ] ; then
                touch ${pub_key_file}
            fi

            gpg -o "${pub_key_file}.tmp"                \
                --armor                                 \
                --export "${SIGKEYID}"


            # Replace pub_key_file only if it's changed
            # ------------------------------------------

            if diff -q "${pub_key_file}" "${pub_key_file}.tmp" &>/dev/null ; then
                rm "${pub_key_file}.tmp"
            else
                mv "${pub_key_file}.tmp" "${pub_key_file}"
            fi

        else
            rm -f "${pub_key_file}"
        fi

        sync-repo ${OUTDIR} ${DEB_REPO_PATH} ${REPO_REQUEST_PATH_PREFIX} ${REQUEST_NUM} ${LP_BUG}

    job_lock "${CONFIGDIR}.lock" unset


    # Filling report file and export results
    # ==================================================

    local DEB_REPO_URL="\"http://${REMOTE_REPO_HOST}/${URL_PREFIX}${DEB_REPO_PATH} ${DEB_DIST_NAME} ${DEB_COMPONENT}\""
    local DEB_BINARIES="$(                              \
        cat ${BINSRCLIST}                               \
        | grep ^Binary                                  \
        | sed 's|^Binary:||; s| ||g'                    \
    )"

    local rep_file="${WRK_DIR}/deb.publish.setenvfile"
    rm -f "${rep_file}"


    # Report:
    # --------------------------------------------------

    info "Creating report in ${rep_file}"

    echo                                     > "${rep_file}"
    echo "DEB_PUBLISH_SUCCEEDED=true"       >> "${rep_file}"
    echo "DEB_DISTRO=${DIST}"               >> "${rep_file}"
    echo "DEB_REPO_URL=${DEB_REPO_URL}"     >> "${rep_file}"
    echo "DEB_PACKAGENAME=${SRC_NAME}"      >> "${rep_file}"
    echo "DEB_VERSION=${NEW_VERSION}"       >> "${rep_file}"
    echo "DEB_BINARIES=${DEB_BINARIES}"     >> "${rep_file}"
    echo "DEB_CHANGE_REVISION=${GERRIT_PATCHSET_REVISION}" \
                                            >> "${rep_file}"
    echo "LP_BUG=${LP_BUG}"                 >> "${rep_file}"

    # --------------------------------------------------

}

main "$@"

exit 0
