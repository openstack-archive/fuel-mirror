#!/bin/bash -ex

[ -f ".publisher-defaults-deb" ] && source .publisher-defaults-deb
source $(dirname $(readlink -e $0))/functions/publish-functions.sh
source $(dirname $(readlink -e $0))/functions/locking.sh

main() {
  local SIGN_STRING=""
  if check-sigul "$SIGKEYID" "$SIGUL_USER" "$SIGUL_ADMIN_PASSWD" ; then
      USE_SIGUL="true"
      SIGN_STRING="true"
  else
      check-gpg && SIGN_STRING="true"
  fi

  ## Download sources from worker
  [ -d $TMP_DIR ] && rm -rf $TMP_DIR
  mkdir -p $TMP_DIR
  rsync -avPzt \
      -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${SSH_OPTS}" \
      ${SSH_USER}${BUILD_HOST}:${PKG_PATH}/ ${TMP_DIR}/ || error "Can't download packages"
  local DEB_BINARIES
  DEB_BINARIES=$(find "$TMP_DIR" -name *.deb | awk -F'/' '{print $NF}' | cut -d'_' -f1 | tr '\n' ',')

  ## Resign source package
  ## FixMe: disabled for discussion: does it really need to sign
  #[ -n "${SIGN_STRING}" ] && \
  #    for _dscfile in $(find ${TMP_DIR} -name "*.dsc") ; do
  #        debsign -pgpg --re-sign -k${SIGKEYID} ${_dscfile}
  #    done

  # Create all repositories

  # Paths
  if [ -n "${CUSTOM_REPO_ID}" ] ; then
      unset LP_BUG
      REQUEST_NUM=${CUSTOM_REPO_ID}
  fi
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

  # Repos
  DEB_UPDATES_DIST_NAME=${DEB_UPDATES_DIST_NAME:-$DEB_DIST_NAME}
  DEB_PROPOSED_DIST_NAME=${DEB_PROPOSED_DIST_NAME:-$DEB_DIST_NAME}
  DEB_SECURITY_DIST_NAME=${DEB_SECURITY_DIST_NAME:-$DEB_DIST_NAME}
  DEB_HOLDBACK_DIST_NAME=${DEB_HOLDBACK_DIST_NAME:-$DEB_DIST_NAME}
  DEB_HOTFIX_DIST_NAME=${DEB_HOTFIX_DIST_NAME:-hotfix}
  DEB_UPDATES_COMPONENT=${DEB_UPDATES_COMPONENT:-$DEB_COMPONENT}
  DEB_PROPOSED_COMPONENT=${DEB_PROPOSED_COMPONENT:-$DEB_COMPONENT}
  DEB_SECURITY_COMPONENT=${DEB_SECURITY_COMPONENT:-$DEB_COMPONENT}
  DEB_HOLDBACK_COMPONENT=${DEB_HOLDBACK_COMPONENT:-$DEB_COMPONENT}
  DEB_HOTFIX_COMPONENT=${DEB_HOTFIX_COMPONENT:-$DEB_COMPONENT}

  local LOCAL_REPO_PATH=${REPO_BASE_PATH}/${DEB_REPO_PATH}
  local DBDIR="+b/db"
  local CONFIGDIR="${LOCAL_REPO_PATH}/conf"
  local DISTDIR="${LOCAL_REPO_PATH}/public/dists/"
  local OUTDIR="+b/public/"
  if [ ! -d "${CONFIGDIR}" ] ; then
      mkdir -p ${CONFIGDIR}
      job_lock ${CONFIGDIR}.lock wait 3600
      for dist_name in ${DEB_DIST_NAME} ${DEB_PROPOSED_DIST_NAME} \
          ${DEB_UPDATES_DIST_NAME} ${DEB_SECURITY_DIST_NAME} \
          ${DEB_HOLDBACK_DIST_NAME} ${DEB_HOTFIX_DIST_NAME} ; do
          cat >> ${CONFIGDIR}/distributions <<- EOF
			Origin: ${ORIGIN}
			Label: ${DEB_DIST_NAME}
			Suite: ${dist_name}
			Codename: ${dist_name}
			Version: ${PRODUCT_VERSION}
			Architectures: amd64 i386 source
			Components: main restricted
			UDebComponents: main restricted
			Contents: . .gz .bz2

			EOF

          reprepro --basedir ${LOCAL_REPO_PATH} --dbdir ${DBDIR} \
              --outdir ${OUTDIR} --distdir ${DISTDIR} --confdir ${CONFIGDIR} \
              export ${dist_name}
          # Fix Codename field
          local release_file="${DISTDIR}/${dist_name}/Release"
          sed "s|^Codename:.*$|Codename: ${DEB_DIST_NAME}|" \
              -i ${release_file}
          rm -f ${release_file}.gpg
          # ReSign Release file
          [ -n "${SIGN_STRING}" ] \
              && gpg --sign --local-user ${SIGKEYID} -ba \
              -o ${release_file}.gpg ${release_file}
      done
      job_lock ${CONFIGDIR}.lock unset
  fi

  DEB_BASE_DIST_NAME=${DEB_DIST_NAME}

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
  if [ "${IS_HOTFIX}" = 'true' ] ; then
      DEB_DIST_NAME=${DEB_HOTFIX_DIST_NAME}
      DEB_COMPONENT=${DEB_HOTFIX_COMPONENT}
  fi

  [ -z "${DEB_COMPONENT}" ] && local DEB_COMPONENT=main
  [ "${IS_RESTRICTED}" = 'true' ] && DEB_COMPONENT=restricted

  local LOCAL_REPO_PATH=${REPO_BASE_PATH}/${DEB_REPO_PATH}
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
        deb) BINDEBLIST="${BINDEBLIST} ${binary}"
             BINDEBNAMES="${BINDEBNAMES} ${binary##*/}"
             ;;
       udeb) BINUDEBLIST="${BINUDEBLIST} ${binary}" ;;
        dsc) BINSRCLIST="${binary}" ;;
    esac
  done

  job_lock ${CONFIGDIR}.lock wait 3600

  local SRC_NAME=$(awk '/^Source:/ {print $2}' ${BINSRCLIST})
  local NEW_VERSION=$(awk '/^Version:/ {print $2}' ${BINSRCLIST} | head -n 1)
  local OLD_VERSION=$(reprepro ${REPREPRO_OPTS} --list-format '${version}\n' \
      listfilter ${DEB_DIST_NAME} "Package (==${SRC_NAME})" | sort -u | head -n 1)
  [ "${OLD_VERSION}" == "" ] && OLD_VERSION=none

  # Remove existing packages for requests-on-review and downgrades
  # TODO: Get rid of removing. Just increase version properly
  if [ "${GERRIT_CHANGE_STATUS}" = "NEW" -o "$IS_DOWNGRADE" == "true" ] ; then
      reprepro ${REPREPRO_OPTS} removesrc ${DEB_DIST_NAME} ${SRC_NAME} ${OLD_VERSION} || :
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
      for dist_name in ${DEB_BASE_DIST_NAME} ${DEB_PROPOSED_DIST_NAME} \
          ${DEB_UPDATES_DIST_NAME} ${DEB_SECURITY_DIST_NAME} \
          ${DEB_HOLDBACK_DIST_NAME} ${DEB_HOTFIX_DIST_NAME}; do
          reprepro ${REPREPRO_COMP_OPTS} --architecture source \
              remove ${dist_name} ${SRC_NAME} || :
          # Fix Codename field and resign Release file if necessary
          local _release_file=${DISTDIR}/${dist_name}/Release
          local _inrelease_file=${DISTDIR}/${dist_name}/InRelease
          if ! gpg --verify "${_release_file}.gpg" "$_release_file" &>/dev/null ; then
              sed "s|^Codename:.*$|Codename: ${DEB_BASE_DIST_NAME}|" -i "$_release_file"
              if [ "$USE_SIGUL" = "true" ] ; then
                  retry -c4 -s1 _sigul "$KEY_PASSPHRASE" -u "$SIGUL_USER" sign-data --armor -o "${_release_file}.gpg" "$SIGKEYID" "$_release_file"
                  retry -c4 -s1 _sigul "$KEY_PASSPHRASE" -u "$SIGUL_USER" sign-text -o "$_inrelease_file" "$SIGKEYID" "$_release_file"
              else
                  gpg --sign --local-user "$SIGKEYID" -ba -o "${_release_file}.gpg" "$_release_file"
                  gpg --sign --local-user "$SIGKEYID" --clearsign -o "$_inrelease_file" "$_release_file"
              fi
          fi
      done
      reprepro ${REPREPRO_COMP_OPTS} includedsc ${DEB_DIST_NAME} ${BINSRCLIST} \
          || error "Can't include packages"
  fi
  # Cleanup files from previous version
  [ "${OLD_VERSION}" != "${NEW_VERSION}" ] \
      && reprepro ${REPREPRO_OPTS} removesrc ${DEB_DIST_NAME} ${SRC_NAME} ${OLD_VERSION}

  # Fix Codename field
  local release_file="${DISTDIR}/${DEB_DIST_NAME}/Release"
  local inrelease_file="${DISTDIR}/${DEB_DIST_NAME}/InRelease"
  sed "s|^Codename:.*$|Codename: ${DEB_BASE_DIST_NAME}|" -i ${release_file}

  # Resign Release file
  rm -f "${release_file}.gpg" "$inrelease_file"
  local pub_key_file="${LOCAL_REPO_PATH}/public/archive-${PROJECT_NAME}${PROJECT_VERSION}.key"
  if [ -n "${SIGN_STRING}" ] ; then
      [ ! -f "${pub_key_file}" ] && touch ${pub_key_file}
      if [ "${USE_SIGUL}" = "true" ] ; then
           retry -c4 -s1 _sigul "$KEY_PASSPHRASE" -u "$SIGUL_USER" sign-data --armor -o "${release_file}.gpg" "${SIGKEYID}" "${release_file}"
           retry -c4 -s1 _sigul "$KEY_PASSPHRASE" -u "$SIGUL_USER" sign-text -o "$inrelease_file" "$SIGKEYID" "$release_file"
           retry -c4 -s1 _sigul "$KEY_PASSPHRASE" -u "$SIGUL_ADMIN" get-public-key "${SIGKEYID}" > "${pub_key_file}.tmp"
      else
          gpg --sign --local-user "$SIGKEYID" -ba -o "${release_file}.gpg" "$release_file"
          gpg --sign --local-user "$SIGKEYID" --clearsign -o "$inrelease_file" "$release_file"
          gpg -o "${pub_key_file}.tmp" --armor --export "$SIGKEYID"
      fi
      if diff -q ${pub_key_file} ${pub_key_file}.tmp &>/dev/null ; then
          rm ${pub_key_file}.tmp
      else
          mv ${pub_key_file}.tmp ${pub_key_file}
      fi
  else
      rm -f ${pub_key_file}
  fi

  # Publish yaml files
  local yaml_file=$(find "$TMP_DIR" -name *.yaml 2>/dev/null)
  if [ -n "$yaml_file" ] ; then
      local yaml_dir=${OUTDIR}/${DEB_DIST_NAME}-versioner
      mkdir -p "$yaml_dir"
      cp -v "$yaml_file" "$yaml_dir"
  fi

  sync-repo ${OUTDIR} ${DEB_REPO_PATH} ${REPO_REQUEST_PATH_PREFIX} ${REQUEST_NUM} ${LP_BUG}
  job_lock ${CONFIGDIR}.lock unset

  rm -f ${WRK_DIR}/deb.publish.setenvfile
  cat > ${WRK_DIR}/deb.publish.setenvfile<<-EOF
	DEB_PUBLISH_SUCCEEDED=true
	DEB_DISTRO=${DIST}
	DEB_REPO_URL="http://${REMOTE_REPO_HOST}/${URL_PREFIX}${DEB_REPO_PATH} ${DEB_DIST_NAME} ${DEB_COMPONENT}"
	DEB_PACKAGENAME=${SRC_NAME}
	DEB_VERSION=${NEW_VERSION}
	DEB_BINARIES=$DEB_BINARIES
	DEB_CHANGE_REVISION=${GERRIT_PATCHSET_REVISION}
	LP_BUG=${LP_BUG}
	EOF
}

main "$@"

exit 0
