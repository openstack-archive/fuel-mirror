#!/bin/bash

#[ -z "$RESYNCONLY" ] && RESYNCONLY=false
[ -z "$REPO_BASE_PATH" ] && REPO_BASE_PATH=${HOME}/pubrepos
[ -z "$PKG_PATH" ] && echo "ERROR: Remote path to built packages is not defined" && exit 1
WRK_DIR=`pwd`
TMP_DIR=${WRK_DIR}/.tmpdir

error () {
  echo
  echo -e "ERROR: $*"
  echo
  exit 1
}

info () {
  echo
  echo -e "INFO: $*"
  echo
}

_sigul () {
   local PASSWD=$1
   shift
   printf '%s\0' "$PASSWD" | sigul --batch $@
}

check-gpg() {
  local RESULT=0
  [ -z "$SIGKEYID" ] && echo "WARNING: No secret keys given" && RESULT=1
  # Test secret keys
  [ $RESULT -eq 0 ] && [ `gpg --list-secret-keys | grep ^sec | grep -c "$SIGKEYID"` -eq 0 ] && error "No secret keys found"
  # Check for password
  if [ $RESULT -eq 0 ] ; then
      timeout 5s bash -c "echo test | gpg -q --no-tty --batch --no-verbose --local-user $SIGKEYID -so - &>/dev/null" \
          || error "Unable to sign with $SIGKEYID key. Passphrase needed!"
  fi
  [ $RESULT -ne 0 ] && echo "WARNING: Fall back to unsigned mode"
  return $RESULT
}

check-sigul() {
  local SIGKEYID=$1
  local SIGUL_USER=$2
  local SIGUL_ADMIN_PASSWD=$3
  local RESULT=0
  # Test of secret key and definiton of sigul
  [ -z "$SIGKEYID" ] && echo "WARNING: No secret keys given" && RESULT=1
  [ -z "$SIGUL_USER" ] && echo "WARNING: No Sigul user given" && RESULT=1
  [ -z "$SIGUL_ADMIN_PASSWD" ] && echo "WARNING: No Sigul Administration's password given" && RESULT=1
  [ -z "$(which sigul)" ] && echo "WARNING: Sigul is not found" && RESULT=1
  # Test of sigul or secret key availability
  if [ $RESULT -eq 0 ] ; then
        retry -c4 -s1 _sigul "$SIGUL_ADMIN_PASSWD" -u "$SIGUL_USER" list-keys > keys_list.tmp
      [ $? -ne 0 ] && echo "WARNING: Something went wrong" && RESULT=1
  fi
  [ $RESULT -eq 0 ] && [ $(grep -c "$SIGKEYID" keys_list.tmp) -ne 1 ] && RESULT=1
  [ $RESULT -ne 0 ] && echo "WARNING:No secret keys found or Sigul is unavailable. Fall back to local signed"
  return $RESULT
}

retry() {
    local count=3
    local sleep=5
    local optname
    while getopts 'c:s:' optname
    do
        case $optname in
            c) count=$OPTARG ;;
            s) sleep=$OPTARG ;;
            ?) return 1 ;;
        esac
    done
    shift $((OPTIND - 1))
    local ec
    while true
    do
        "$@" && true
        ec=$?
        (( count-- ))
        if [[ $ec -eq 0 || $count -eq 0 ]]
        then
            break
        else
            sleep "$sleep"
        fi
    done
    return "$ec"
}

sync-repo() {
  local LOCAL_DIR=$1
  local REMOTE_DIR=$2
  local REQUEST_PATH_PREFIX=$3
  [ -n "$4" ] && local REQUEST_NUM=$4
  [ -n "$5" ] && local LP_BUG=$5

  RSYNC_USER=${RSYNC_USER:-"mirror-sync"}
  [ -z "$REMOTE_REPO_HOST" ] && error "Remote host to sync is not defined."
  [ ! -d "${LOCAL_DIR}" ] && error "Repository ${LOCAL_DIR} doesn't exist!"
  ## SYNC
  source $(dirname `readlink -e $0`)/functions/rsync_functions.sh
  mirrors_fail=""
  for host in $REMOTE_REPO_HOST; do
    # sync files to remote host
    # $1 - remote host
    # $2 - rsync user
    # $3 - local dir
    # $4 - remote dir
    if [ "$GERRIT_CHANGE_STATUS" == "NEW" ] ; then
        rsync_create_dir $host $RSYNC_USER ${REQUEST_PATH_PREFIX}
        if [ -n "$LP_BUG" ] && [ -n "$REQUEST_NUM" ] ; then
            # Remove existing REQUEST_NUM repository and set it as symlink to LP_BUG one
            if [ $(rsync_list_links $host $RSYNC_USER ${REQUEST_PATH_PREFIX} | grep -c "^${REQUEST_NUM} ") -eq 0 ] ; then
                rsync_delete_dir $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM}
            else
                rsync_delete_file $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM}
            fi
            rsync_create_symlink $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM} ${LP_BUG}
            REMOTE_DIR=${REQUEST_PATH_PREFIX}${LP_BUG}/${REMOTE_DIR}
        else
            # Symlinked REQUEST_NUM repository should be removed in order to not affect LP_BUG one
            [ $(rsync_list_links $host $RSYNC_USER ${REQUEST_PATH_PREFIX} | grep -c "^${REQUEST_NUM} ") -gt 0 ] \
                && rsync_delete_file $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM}
            REMOTE_DIR=${REQUEST_PATH_PREFIX}${REQUEST_NUM}/${REMOTE_DIR}
        fi
    elif [ -n "$REQUEST_PATH_PREFIX" ] ; then
        # Remove unused request repos
        if [ -n "$REQUEST_NUM" ] ; then
            if [ $(rsync_list_links $host $RSYNC_USER ${REQUEST_PATH_PREFIX} | grep -c "^${REQUEST_NUM} ") -eq 0 ] ; then
                rsync_delete_dir $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM}
            else
                rsync_delete_file $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM}
            fi
            [ $(rsync_list_files $host $RSYNC_USER ${REQUEST_PATH_PREFIX} | grep -cF $REQUEST_NUM) -gt 0 ] \
              && rsync_delete_file $host $RSYNC_USER ${REQUEST_PATH_PREFIX}${REQUEST_NUM}.target.txt
        fi
        # Do not remove LP_BUG repo until all linked repos removed
        [ -n "$LP_BUG" ] \
            && [ $(rsync_list_links $host $RSYNC_USER ${REQUEST_PATH_PREFIX} | grep -cF $LP_BUG) -eq 0 ] \
            && rsync_delete_dir $host $RSYNC_USER ${REQUEST_PATH_PREFIX}/$LP_BUG
    fi
    rsync_transfer $host $RSYNC_USER $LOCAL_DIR $REMOTE_DIR || mirrors_fail+=" ${host}"
  done
  #if [[ -n "$mirrors_fail" ]]; then
  #  echo Some mirrors failed to update: $mirrors_fail
  #  exit 1
  #else
  #  export MIRROR_VERSION="${TGTDIR}"
  #  export MIRROR_BASE="http://$RSYNCHOST_MSK/fwm/files/${MIRROR_VERSION}"
  #  echo "MIRROR = ${mirror}" > ${WORKSPACE:-"."}/mirror_staging.txt
  #  echo "MIRROR_VERSION = ${MIRROR_VERSION}" >> ${WORKSPACE:-"."}/mirror_staging.txt
  #  echo "MIRROR_BASE = $MIRROR_BASE" >> ${WORKSPACE:-"."}/mirror_staging.txt
  #  echo "FUEL_MAIN_BRANCH = ${FUEL_MAIN_BRANCH}" >> ${WORKSPACE:-"."}/mirror_staging.txt
  #  echo "Updated: ${MIRROR_VERSION}<br> <a href='http://mirror.fuel-infra.org//${FILESROOT}/${TGTDIR}'>ext</a> <a href='http://${RSYNCHOST_MSK}/${FILESROOT}/${TGTDIR}'>msk</a> <a href='http://${RSYNCHOST_SRT}/${FILESROOT}/${TGTDIR}'>srt</a> <a href='http://${RSYNCHOST_KHA}/${FILESROOT}/${TGTDIR}'>kha</a>"
  #fi
}
