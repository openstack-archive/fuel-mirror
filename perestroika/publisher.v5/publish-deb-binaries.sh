#!/bin/bash -ex

[ -f ".publisher-defaults-deb" ] && source .publisher-defaults-deb
source $(dirname $(readlink -e $0))/functions/publish-functions.sh
source $(dirname $(readlink -e $0))/functions/locking.sh

# Used global envvars
# ~~~~~~~~~~~~~~~~~~~

# Mixed from publish-functions.sh
# TMP_DIR           path to temporary directory
# WRK_DIR           path to cwd

# Input parameters for downloading package(s) from given jenkins-worker
# SSH_OPTS          ssh options for rsync (could be empty)
# SSH_USER          user who have ssh access to the worker (could be empty)
# BUILD_HOST        fqdn/ip of worker
# PKG_PATH          path to package which should be download

# CUSTOM_REPO_ID
# REPO_REQUEST_PATH_PREFIX
# LP_BUG
# GERRIT_CHANGE_STATUS
# DEB_REPO_PATH
# ORIGIN
# DEB_DIST_NAME
# DEB_PROPOSED_DIST_NAME
# DEB_UPDATES_DIST_NAME
# DEB_SECURITY_DIST_NAME
# DEB_HOLDBACK_DIST_NAME
# PRODUCT_VERSION

# Directives for using different kinds of workflows which define output repos for packages
# IS_UPDATES         updates workflow -
# IS_HOLDBACK
# IS_SECURITY
# IS_RESTRICTED
# IS_DOWNGRADE       downgrade package

# GERRIT_PATCHSET_REVISION
# REMOTE_REPO_HOST
# SIGKEYID
# PROJECT_NAME
# PROJECT_VERSION
# DEB_COMPONENT
# DEB_UPDATES_COMPONENT
# DEB_PROPOSED_COMPONENT
# DEB_SECURITY_COMPONENT
# DEB_HOLDBACK_COMPONENT
# DIST

main() {
    local SIGN_STRING=""
    check-gpg && SIGN_STRING="true"

    # Reinitialize temp directory
    [ -d "${TMP_DIR}" ] && rm -rf "${TMP_DIR}"
    mkdir -p "${TMP_DIR}"

    ## Download sources from worker
    rsync -avPzt \
          -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${SSH_OPTS}" \
          # FIXME: Looks like we have a bug here and user and host should be separated.
          #        We didn't shoot-in-the leg IRL because we don't pass this param
          #        Prop. sol: [ -z "${SSH_USER}" ] && SSH_USER="${SSH_USER}@"
          "${SSH_USER}${BUILD_HOST}:${PKG_PATH}/" \
          "${TMP_DIR}/" \
    || error "Can't download packages"

    ## Resign source package
    ## FixMe: disabled for discussion: does it really need to sign
    #[ -n "${SIGN_STRING}" ] && \
    #    for _dscfile in $(find ${TMP_DIR} -name "*.dsc") ; do
    #        debsign -pgpg --re-sign -k${SIGKEYID} ${_dscfile}
    #    done

    # Create all repositories


    # Crunch for using custom namespace for publishing packages
    # When CUSTOM_REPO_ID is given, then:
    # - packages are not grouped by bug
    # - CUSTOM_REPO_ID is used instead of request serial number

    if [ -n "${CUSTOM_REPO_ID}" ] ; then
        unset LP_BUG
        REQUEST_NUM="${CUSTOM_REPO_ID}"
    fi

    # Defining url prefix and paths:
    # - only newly created patchsets have prefixes
    # - if LP_BUG is given then it replaces REQUEST_NUM
    # FIXME: do not mutate REPO_BASE_PATH, use local variable instead
    local URL_PREFIX=
    if [ "${GERRIT_CHANGE_STATUS}" = "NEW" ] ; then
        if [ -n "${LP_BUG}" ] ; then
            REPO_BASE_PATH="${REPO_BASE_PATH}/${REPO_REQUEST_PATH_PREFIX}${LP_BUG}"
            URL_PREFIX="${REPO_REQUEST_PATH_PREFIX}${LP_BUG}/"
        else
            REPO_BASE_PATH="${REPO_BASE_PATH}/${REPO_REQUEST_PATH_PREFIX}${REQUEST_NUM}"
            URL_PREFIX="${REPO_REQUEST_PATH_PREFIX}${REQUEST_NUM}/"
        fi
    else
        REPO_BASE_PATH="${REPO_BASE_PATH}/${REPO_REQUEST_PATH_PREFIX}"
        URL_PREFIX=""
    fi

    # Repos
    local LOCAL_REPO_PATH="${REPO_BASE_PATH}/${DEB_REPO_PATH}"
    local DBDIR="+b/db"
    local CONFIGDIR="${LOCAL_REPO_PATH}/conf"
    local DISTDIR="${LOCAL_REPO_PATH}/public/dists/"
    local OUTDIR="+b/public/"
    if [ ! -d "${CONFIGDIR}" ] ; then
        mkdir -p "${CONFIGDIR}"
        job_lock "${CONFIGDIR}.lock" wait 3600

        local distributions=

        for dist_name in "${DEB_DIST_NAME}"          \
                         "${DEB_PROPOSED_DIST_NAME}" \
                         "${DEB_UPDATES_DIST_NAME}"  \
                         "${DEB_SECURITY_DIST_NAME}" \
                         "${DEB_HOLDBACK_DIST_NAME}" ; do


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

            reprepro --basedir "${LOCAL_REPO_PATH}" \
                     --dbdir   "${DBDIR}"           \
                     --outdir  "${OUTDIR}"          \
                     --distdir "${DISTDIR}"         \
                     --confdir "${CONFIGDIR}"       \
                     export "${dist_name}"

            # Fix Codename field
            local release_file="${DISTDIR}/${dist_name}/Release"

            sed "s|^Codename:.*$|Codename: ${DEB_DIST_NAME}|" -i "${release_file}"
            rm -f "${release_file}.gpg"

            # ReSign Release file
            if [ -n "${SIGN_STRING}" ] ; then
                gpg --sign \
                    --local-user "${SIGKEYID}" \
                    -ba \
                    -o ${release_file}.gpg ${release_file}
            fi
        done
        job_lock ${CONFIGDIR}.lock unset
    fi


    DEB_BASE_DIST_NAME="${DEB_DIST_NAME}"

    # Setting defaults

    # dist names
    [ -z "${DEB_UPDATES_DIST_NAME}" ]  && DEB_UPDATES_DIST_NAME="${DEB_DIST_NAME}"
    [ -z "${DEB_PROPOSED_DIST_NAME}" ] && DEB_PROPOSED_DIST_NAME="${DEB_DIST_NAME}"
    [ -z "${DEB_SECURITY_DIST_NAME}" ] && DEB_SECURITY_DIST_NAME="${DEB_DIST_NAME}"
    [ -z "${DEB_HOLDBACK_DIST_NAME}" ] && DEB_HOLDBACK_DIST_NAME="${DEB_DIST_NAME}"

    # components
    [ -z "${DEB_UPDATES_COMPONENT}" ]  && DEB_UPDATES_COMPONENT="${DEB_COMPONENT}"
    [ -z "${DEB_PROPOSED_COMPONENT}" ] && DEB_PROPOSED_COMPONENT="${DEB_COMPONENT}"
    [ -z "${DEB_SECURITY_COMPONENT}" ] && DEB_SECURITY_COMPONENT="${DEB_COMPONENT}"
    [ -z "${DEB_HOLDBACK_COMPONENT}" ] && DEB_HOLDBACK_COMPONENT="${DEB_COMPONENT}"

    # overrides for different kinds of input directives "IS_XXX"

    if [ "${IS_UPDATES}" = 'true' ] ; then
        DEB_DIST_NAME=${DEB_PROPOSED_DIST_NAME}
        DEB_COMPONENT=${DEB_PROPOSED_COMPONENT}
    fi
    if [ "${IS_HOLDBACK}" = 'true' ] ; then
        DEB_DIST_NAME=${DEB_HOLDBACK_DIST_NAME}
        DEB_COMPONENT=${DEB_HOLDBACK_COMPONENT}
    fi
    if [ "${IS_SECURITY}" = 'true' ] ; then
      DEB_DIST_NAME=${DEB_SECURITY_DIST_NAME}
      DEB_COMPONENT=${DEB_SECURITY_COMPONENT}
    fi

    [ -z "${DEB_COMPONENT}" ] && local DEB_COMPONENT=main

    # FIXME: looks like "local" is missing
    [ "${IS_RESTRICTED}" = 'true' ] && DEB_COMPONENT=restricted

    local LOCAL_REPO_PATH="${REPO_BASE_PATH}/${DEB_REPO_PATH}"
    local CONFIGDIR="${LOCAL_REPO_PATH}/conf"
    local DBDIR="+b/db"
    local DISTDIR="${LOCAL_REPO_PATH}/public/dists/"
    local OUTDIR="${LOCAL_REPO_PATH}/public/"
    local REPREPRO_OPTS="--verbose --basedir ${LOCAL_REPO_PATH} --dbdir ${DBDIR} \
      --outdir ${OUTDIR} --distdir ${DISTDIR} --confdir ${CONFIGDIR}"
    local REPREPRO_COMP_OPTS="${REPREPRO_OPTS} --component ${DEB_COMPONENT}"

    # Parse incoming files
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
                BINSRCLIST="${binary}"
            ;;
        esac
    done

    job_lock "${CONFIGDIR}.lock" wait 3600

    local SRC_NAME=$(awk '/^Source:/ {print $2}' ${BINSRCLIST})
    local NEW_VERSION=$(awk '/^Version:/ {print $2}' ${BINSRCLIST} | head -n 1)
    local OLD_VERSION=$(reprepro ${REPREPRO_OPTS} --list-format '${version}\n' \
                        listfilter ${DEB_DIST_NAME} "Package (==${SRC_NAME})" | sort -u | head -n 1)
    [ "${OLD_VERSION}" == "" ] && OLD_VERSION=none

    # Remove existing packages for requests-on-review and downgrades
    # TODO: Get rid of removing. Just increase version properly
    if [ "${GERRIT_CHANGE_STATUS}" = "NEW" -o "${IS_DOWNGRADE}" == "true" ] ; then
        reprepro ${REPREPRO_OPTS} removesrc "${DEB_DIST_NAME}" "${SRC_NAME}" "${OLD_VERSION}" \
        || true
    fi
    # Add .deb binaries
    if [ "${BINDEBLIST}" != "" ]; then
        reprepro ${REPREPRO_COMP_OPTS} includedeb ${DEB_DIST_NAME} ${BINDEBLIST} \
        || error "Can't include packages"
    fi
    # Add .udeb binaries
    if [ "${BINUDEBLIST}" != "" ]; then
        reprepro ${REPREPRO_COMP_OPTS} includeudeb ${DEB_DIST_NAME} ${BINUDEBLIST} \
        || error "Can't include packages"
    fi

    # Replace sources
    # TODO: Get rid of replacing. Just increase version properly
    if [ "${BINSRCLIST}" != "" ]; then
        reprepro ${REPREPRO_COMP_OPTS} --architecture source \
                 remove ${DEB_DIST_NAME} ${SRC_NAME} || :
        reprepro ${REPREPRO_COMP_OPTS} includedsc ${DEB_DIST_NAME} ${BINSRCLIST} \
        || error "Can't include packages"
    fi
    # Cleanup files from previous version
    [ "${OLD_VERSION}" != "${NEW_VERSION}" ] \
        && reprepro ${REPREPRO_OPTS} removesrc ${DEB_DIST_NAME} ${SRC_NAME} ${OLD_VERSION}

    # Fix Codename field
    local release_file="${DISTDIR}/${DEB_DIST_NAME}/Release"
    sed "s|^Codename:.*$|Codename: ${DEB_BASE_DIST_NAME}|" -i ${release_file}

    # Resign Release file
    rm -f "${release_file}.gpg"

    local pub_key_file="${LOCAL_REPO_PATH}/public/archive-${PROJECT_NAME}${PROJECT_VERSION}.key"
    if [ -n "${SIGN_STRING}" ] ; then
        gpg --sign --local-user "${SIGKEYID}" -ba -o "${release_file}.gpg" "${release_file}"

        # fixme: coulde we just touch?
        [ ! -f "${pub_key_file}" ] && touch ${pub_key_file}

        gpg -o "${pub_key_file}.tmp" --armor --export "${SIGKEYID}"
        if diff -q "${pub_key_file}" "${pub_key_file}.tmp" &>/dev/null ; then
            rm "${pub_key_file}.tmp"
        else
            mv "${pub_key_file}.tmp" "${pub_key_file}"
        fi
    else
        rm -f "${pub_key_file}"
    fi

    sync-repo "${OUTDIR}" "${DEB_REPO_PATH}" "${REPO_REQUEST_PATH_PREFIX}" "${REQUEST_NUM}" "${LP_BUG}"
    job_lock "${CONFIGDIR}.lock" unset

    # Filling report file and export results:
    rm -f "${WRK_DIR}/deb.publish.setenvfile"
    echo > "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_PUBLISH_SUCCEEDED=true"       >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_DISTRO=${DIST}"               >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_REPO_URL=\"http://${REMOTE_REPO_HOST}/${URL_PREFIX}${DEB_REPO_PATH} ${DEB_DIST_NAME} ${DEB_COMPONENT}\"" \
                                            >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_PACKAGENAME=${SRC_NAME}"      >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_VERSION=${NEW_VERSION}"       >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_BINARIES=$(cat ${BINSRCLIST} | grep ^Binary | sed 's|^Binary:||; s| ||g')" \
                                            >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "DEB_CHANGE_REVISION=${GERRIT_PATCHSET_REVISION}" \
                                            >> "${WRK_DIR}/deb.publish.setenvfile"
    echo "LP_BUG=${LP_BUG}"                 >> "${WRK_DIR}/deb.publish.setenvfile"

}

main

exit 0
