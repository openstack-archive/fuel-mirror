#!/bin/bash
[ -z "$GERRIT_USER" ] && GERRIT_USER='openstack-ci-jenkins'
[ -z "$GERRIT_HOST" ] && GERRIT_HOST=$gerrit_host
[ -z "$GERRIT_PORT" ] && GERRIT_PORT=$gerrit_port
[ -z "$GERRIT_PORT" ] && GERRIT_PORT=29418
[ -z "$GERRIT_SCHEME" ] && GERRIT_SCHEME="ssh"
URL="${GERRIT_SCHEME}://${GERRIT_USER}@${GERRIT_HOST}:${GERRIT_PORT}"
GITDATA=${HOME}/gitdata/$GERRIT_HOST
METADATA=${HOME}/repometadata
PKG_DIR=${HOME}/built_packages
EXCLUDES='--exclude-vcs'
WRKDIR=`pwd`
MYOUTDIR=${WRKDIR}/wrk-build
BUILDDIR=${MYOUTDIR}/src-to-build
rm -rf $BUILDDIR
mkdir -p $BUILDDIR
[ ! -d "$PKG_DIR" ] && mkdir -p $PKG_DIR
[ -f "${WRKDIR}/buildlog.txt" ] && rm -f ${WRKDIR}/buildlog.txt

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

job_lock() {
    local LOCKFILE=$1
    local TIMEOUT=600
    shift
    fd=15
    eval "exec $fd>$LOCKFILE"
    if [ "$1" = "set" ]; then
        flock --timeout $TIMEOUT -x $fd
    elif [ "$1" = "unset" ]; then
        flock -u $fd
    fi
}

request_is_merged () {
  local REF=$1
  local CHANGENUMBER=`echo $REF | cut -d '/' -f4`
  local result=1
  local status=`ssh ${GERRIT_USER}@${GERRIT_HOST} -p $GERRIT_PORT gerrit query --format=TEXT $CHANGENUMBER | egrep -o " +status:.*" | awk -F': ' '{print $2}'`
  [ "$status" == "MERGED" ] && local result=0
  return $result
}

set_default_params () {
  [ -z "$PROJECT_NAME" ] && error "Project name is not defined! Exiting!"
  [ -z "$PROJECT_VERSION" ] && error "Project version is not defined! Exiting!"
  [ -z "$SECUPDATETAG" ] && local SECUPDATETAG="^Security-update"
  [ -z "$IS_SECURITY" ] && IS_SECURITY='false'
  if [ -n "$GERRIT_PROJECT" ]; then
    GERRIT_CHANGE_STATUS="NEW"
    if [ -n "$GERRIT_REFSPEC" ]; then
      request_is_merged $GERRIT_REFSPEC && GERRIT_CHANGE_STATUS="MERGED"
    else
      # Support ref-updated gerrit event
      GERRIT_CHANGE_STATUS="REF_UPDATED"
      GERRIT_BRANCH=$GERRIT_REFNAME
    fi
    if [ -n "$GERRIT_CHANGE_COMMIT_MESSAGE" ] ; then
        local GERRIT_MEGGASE="`echo $GERRIT_CHANGE_COMMIT_MESSAGE | base64 -d || :`"
    fi
    if [ "$GERRIT_CHANGE_STATUS" == "NEW" ] ; then
      REQUEST_NUM="CR-$GERRIT_CHANGE_NUMBER"
      local _LP_BUG=`echo "$GERRIT_TOPIC" | egrep -o "group/[0-9]+" | cut -d'/' -f2`
      #[ -z "$_LP_BUG" ] && _LP_BUG=`echo "$GERRIT_MEGGASE" | egrep -i -o "(closes|partial|related)-bug: ?#?[0-9]+" | sort -u | head -1 | awk -F'[: #]' '{print $NF}'`
      [ -n "$_LP_BUG" ] && LP_BUG="LP-$_LP_BUG"
    else
      if [ -n "$GERRIT_MESSAGE" ] ; then
         if [ `echo $GERRIT_MESSAGE | grep -c \"$SECUPDATETAG\"` -gt 0 ] ; then
            IS_SECURITY='true'
         fi
      fi
    fi
    # Detect packagename
    PACKAGENAME=${GERRIT_PROJECT##*/}
    [ "${PACKAGENAME##*-}" == "build" ] && PACKAGENAME=${PACKAGENAME%-*}
    SRC_PROJECT=${SRC_PROJECT_PATH}/$PACKAGENAME
    [ "$IS_OPENSTACK" == "true" ] && SPEC_PROJECT=${SPEC_PROJECT_PATH}/${PACKAGENAME}${SPEC_PROJECT_SUFFIX}
    case $GERRIT_PROJECT in
      "$SRC_PROJECT" ) SOURCE_REFSPEC=$GERRIT_REFSPEC ;;
      "$SPEC_PROJECT" ) SPEC_REFSPEC=$GERRIT_REFSPEC ;;
    esac
    SOURCE_BRANCH=$GERRIT_BRANCH
    [ "$IS_OPENSTACK" == "true" ] && SPEC_BRANCH=$GERRIT_BRANCH
  fi
  [ -z "$PACKAGENAME" ] && error "Package name is not defined! Exiting!"
  [ -z "$SOURCE_BRANCH" ] && error "Source branch is not defined! Exiting!"
  [ "$IS_OPENSTACK" == "true" ] && [ -z "$SPEC_BRANCH" ] && SPEC_BRANCH=$SOURCE_BRANCH
  [ "$IS_OPENSTACK" == "true" ] && SPEC_PROJECT=${SPEC_PROJECT_PATH}/${PACKAGENAME}${SPEC_PROJECT_SUFFIX}
  SRC_PROJECT=${SRC_PROJECT_PATH}/$PACKAGENAME
}

fetch_upstream () {
  # find corresponding requests
  if [ -n "$SPEC_PROJECT" -a "${GERRIT_TOPIC%/*}" = "spec" ] ; then
      local CORR_GERRIT_PROJECT=$SRC_PROJECT
      [ "$GERRIT_PROJECT" == "$SRC_PROJECT" ] && CORR_GERRIT_PROJECT=$SPEC_PROJECT
      local search_string="topic:${GERRIT_TOPIC} branch:${GERRIT_BRANCH} project:${CORR_GERRIT_PROJECT} -status:abandoned"
      local CORR_CHANGE=`ssh -p $GERRIT_PORT ${GERRIT_USER}@$GERRIT_HOST gerrit query --current-patch-set \'${search_string}\'`
      local CORR_CHANGE_REFSPEC="`echo \"${CORR_CHANGE}\" | grep 'ref:' | awk '{print $NF}'`"
      local CORR_CHANGE_NUMBER=`echo $CORR_CHANGE_REFSPEC | cut -d'/' -f4`
      local CORR_PATCHSET_NUMBER=`echo $CORR_CHANGE_REFSPEC | cut -d'/' -f5`
      local CORR_CHANGE_URL=`echo "${CORR_CHANGE}" | grep 'url:' | awk '{print $NF}'`
      local CORR_CHANGE_STATUS=`echo "${CORR_CHANGE}" | grep 'status:' | awk '{print $NF}'`

      local corr_ref_count=`echo "$CORR_CHANGE_REFSPEC" | wc -l`
      [ $corr_ref_count -gt 1 ] && error "ERROR: Multiple corresponding changes found!"
      if [ -n "$CORR_CHANGE_NUMBER" ] ; then
          # Provide corresponding change to vote script
          cat > ${WRKDIR}/corr.setenvfile <<-EOL
			CORR_CHANGE_NUMBER=$CORR_CHANGE_NUMBER
			CORR_PATCHSET_NUMBER=$CORR_PATCHSET_NUMBER
			CORR_CHANGE_URL=$CORR_CHANGE_URL
			CORR_CHANGE_REFSPEC=$CORR_CHANGE_REFSPEC
			EOL
      fi
      # Do not perform build stage if corresponding CR is not merged
      if [ -n "${CORR_CHANGE_STATUS}" ] && [ "$GERRIT_CHANGE_STATUS" == "MERGED" ] && [ "$CORR_CHANGE_STATUS" != "MERGED" ] ; then
          echo "SKIPPED=1" >> ${WRKDIR}/corr.setenvfile
          error "Skipping build due to unmerged status of corresponding change ${CORR_CHANGE_URL}"
      fi
  fi

  # Do not clone projects every time. It makes gerrit sad. Cache it!
  for prj in $SRC_PROJECT $SPEC_PROJECT; do
    # Update code base cache
    [ -d ${GITDATA} ] || mkdir -p ${GITDATA}
    if [ ! -d ${GITDATA}/$prj ]; then
      info "Cache for $prj doesn't exist. Cloning to ${HOME}/gitdata/$prj"
      mkdir -p ${GITDATA}/$prj
      # Lock cache directory
      job_lock ${GITDATA}/${prj}.lock set
      pushd ${GITDATA} &>/dev/null
      info "Cloning sources from $URL/$prj.git ..."
      git clone "$URL/$prj.git" "$prj"
      popd &>/dev/null
    else
      # Lock cache directory
      job_lock ${GITDATA}/${prj}.lock set
      info "Updating cache for $prj"
      pushd ${GITDATA}/$prj &>/dev/null
      info "Fetching sources from $URL/$prj.git ..."
      # Replace git remote user
      local remote=`git remote -v | head -1 | awk '{print $2}' | sed "s|//.*@|//${GERRIT_USER}@|"`
      git remote rm origin
      git remote add origin $remote
      # Update gitdata
      git fetch --all
      popd &>/dev/null
    fi
    if [ "$prj" == "$SRC_PROJECT" ]; then
      local _DIRSUFFIX=src
      local _BRANCH=$SOURCE_BRANCH
      [ -n "$SOURCE_REFSPEC" ] && local _REFSPEC=$SOURCE_REFSPEC
    fi
    if [ "$prj" == "$SPEC_PROJECT" ]; then
      local _DIRSUFFIX=spec
      local _BRANCH=$SPEC_BRANCH
      [ -n "$SPEC_REFSPEC" ] && local _REFSPEC=$SPEC_REFSPEC
    fi
    [ -e "${MYOUTDIR}/${PACKAGENAME}-${_DIRSUFFIX}" ] && rm -rf "${MYOUTDIR}/${PACKAGENAME}-${_DIRSUFFIX}"
    info "Getting $_DIRSUFFIX from $URL/$prj.git ..."
    cp -R ${GITDATA}/${prj} ${MYOUTDIR}/${PACKAGENAME}-${_DIRSUFFIX}
    # Unlock cache directory
    job_lock ${GITDATA}/${prj}.lock unset
    pushd ${MYOUTDIR}/${PACKAGENAME}-${_DIRSUFFIX} &>/dev/null
    switch_to_revision $_BRANCH
    # Get code from HEAD if change is merged
    [ "$GERRIT_CHANGE_STATUS" == "MERGED" ] && unset _REFSPEC
    # If _REFSPEC specified switch to it
    if [ -n "$_REFSPEC" ] ; then
        switch_to_changeset $prj $_REFSPEC
    else
       [ "$prj" == "${CORR_GERRIT_PROJECT}" ] && [ -n "${CORR_CHANGE_REFSPEC}" ] && switch_to_changeset $prj $CORR_CHANGE_REFSPEC
    fi
    popd &>/dev/null
    case $_DIRSUFFIX in
       src) gitshasrc=$gitsha
        ;;
      spec) gitshaspec=$gitsha
        ;;
      *) error "Unknown project type"
        ;;
    esac
    unset _DIRSUFFIX
    unset _BRANCH
    unset _REFSPEC
  done
}

switch_to_revision () {
  info "Switching to branch $*"
  if ! git checkout $*; then
    error "$* not accessible by default clone/fetch"
  else
    git reset --hard origin/$*
    gitsha=`git log -1 --pretty="%h"`
  fi
}

switch_to_changeset () {
  info "Switching to changeset $2"
  git fetch "$URL/$1.git" $2
  git checkout FETCH_HEAD
  gitsha=`git log -1 --pretty="%h"`
}

get_last_commit_info () {
  if [ -n "$1" ] ; then
    pushd $1 &>/dev/null
    message="$(git log -n 1 --pretty=format:%B)"
    author=$(git log -n 1 --pretty=format:%an)
    email=$(git log -n 1 --pretty=format:%ae)
    cdate=$(git log -n 1 --pretty=format:%ad | cut -d' ' -f1-3,5)
    commitsha=$(git log -n 1 --pretty=format:%h)
    lastgitlog=$(git log --pretty="%h|%ae|%an|%s" -n 10)
    popd &>/dev/null
  fi
}

fill_buildresult () {
    #$status $time $PACKAGENAME $pkgtype
    local status=$1
    local time=$2
    local packagename=$3
    local pkgtype=$4
    local xmlfilename=${WRKDIR}/buildresult.xml
    local failcnt=0
    local buildstat="Succeeded"
    [ "$status" != "0" ] && failcnt=1 && buildstat="Failed"
    echo "<testsuite name=\"Package build\" tests=\"Package build\" errors=\"0\" failures=\"$failcnt\" skip=\"0\">" > $xmlfilename
    echo -n "<testcase classname=\"$pkgtype\" name=\"$packagename\" time=\"0\"" >> $xmlfilename
    if [ "$failcnt" == "0" ] ; then
        echo "/>" >> $xmlfilename
    else
        echo ">" >> $xmlfilename
        echo "<failure type=\"Failure\" message=\"$buildstat\">" >> $xmlfilename
        if [ -f "${WRKDIR}/buildlog.txt" ] ; then
            cat ${WRKDIR}/buildlog.txt | sed -n '/^dpkg: error/,/^Package installation failed/p' | egrep -v '^Get|Selecting|Unpacking|Preparing' >> $xmlfilename || :
            cat ${WRKDIR}/buildlog.txt | sed -n '/^The following information may help to resolve the situation/,/^Package installation failed/p' >> $xmlfilename || :
            cat ${WRKDIR}/buildlog.txt | grep -B 20 '^dpkg-buildpackage: error' >> $xmlfilename || :
            cat ${WRKDIR}/buildlog.txt | grep -B 20 '^EXCEPTION:' >> $xmlfilename || :
        fi
        if [ -f "${WRKDIR}/rootlog.txt" ] ; then
            cat ${WRKDIR}/rootlog.txt | sed -n '/No Package found/,/Exception/p' >> $xmlfilename || :
            cat ${WRKDIR}/rootlog.txt | sed -n '/Error: /,/You could try using --skip-broken to work around the problem/p' >> $xmlfilename || :
        fi
        echo "</failure>" >> $xmlfilename
        echo "</testcase>" >> $xmlfilename
    fi
    echo "</testsuite>" >> $xmlfilename
}
