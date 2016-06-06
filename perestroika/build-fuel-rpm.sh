#!/bin/bash

set -o xtrace
set -o errexit

[ -f .fuel-default ] && source .fuel-default
BINDIR=$(dirname `readlink -e $0`)
source "${BINDIR}"/build-functions.sh

main () {
    set_default_params
    [ -n "$GERRIT_BRANCH" ] && SOURCE_BRANCH=$GERRIT_BRANCH && SOURCE_REFSPEC=$GERRIT_REFSPEC
    [ -n "$GERRIT_PROJECT" ] && SRC_PROJECT=$GERRIT_PROJECT
    PACKAGENAME=${SRC_PROJECT##*/}

    # If we are triggered from gerrit env, let's keep current workflow,
    # and fetch code from upstream
    # otherwise let's define custom path to already prepared source code
    # using $CUSTOM_SRC_PATH variable
    if [ -n "${GERRIT_BRANCH}" ]; then
        # Get package tree from gerrit
        fetch_upstream
        local _srcpath="${MYOUTDIR}/${PACKAGENAME}-src"
    else
        local _srcpath="${CUSTOM_SRC_PATH}"
    fi

    local _specpath="${_srcpath}/specs"

    # Get last commit info
    # $message $author $email $cdate $commitsha $lastgitlog
    get_last_commit_info ${_srcpath}

    # Update specs
    local specfile=`find $_specpath -name *.spec`
    local version=`rpm -q --specfile $specfile --queryformat '%{VERSION}\n' | head -1`
    local release=`rpm -q --specfile $specfile --queryformat '%{RELEASE}\n' | head -1`
    ## Add changelog section if it doesn't exist
    [ `cat ${specfile} | grep -c '^%changelog'` -eq 0 ] && echo "%changelog" >> ${specfile}
    local _rev=`git -C $_srcpath rev-list --no-merges origin/${SOURCE_BRANCH} | wc -l`
    # if gitshasrc is not defined (we are not using fetch_upstream), let's do it
    [ -n "${gitshasrc}" ] || local gitshasrc=$(git -C $_srcpath log -1 --pretty="%h")
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && _rev=$(( $_rev + 1 ))
    local release="1.mos${_rev}"
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && release="${release}.git.${gitshasrc}"
    local TAR_NAME=${PACKAGENAME}-${version}.tar.gz
    # Update version and changelog
    sed -i "s|Version:.*$|Version: ${version}|" $specfile
    sed -i "s|Release:.*$|Release: ${release}|" $specfile
    sed -i "s|Source0:.*$|Source0: ${TAR_NAME}|" $specfile
    ## Update changelog
    local firstline=1
    if [ ! -z "$lastgitlog" ]; then
        sed -i "/%changelog/i%newchangelog" ${specfile}
        echo "$lastgitlog" | while read LINE; do
            local commitid=`echo "$LINE" | cut -d'|' -f1`
            local email=`echo "$LINE" | cut -d'|' -f2`
            local author=`echo "$LINE" | cut -d'|' -f3`
            # Get current date to avoid wrong chronological order in %changelog section
            local date=`LC_TIME=C date +"%a %b %d %Y"`
            local subject=`echo "$LINE" | cut -d'|' -f4`
            [ $firstline == 1 ] && sed -i "/%changelog/i\* $date $author \<${email}\> \- ${version}-${release}" ${specfile}
            sed -i "/%changelog/i\- $commitid $subject" ${specfile}
            firstline=0
        done
    fi
    sed -i '/%changelog/i\\' ${specfile}
    sed -i '/^%changelog/d' ${specfile}
    sed -i 's|^%newchangelog|%changelog|' ${specfile}
    cp ${specfile} ${BUILDDIR}/

    # Prepare source tarball
    pushd $_srcpath &>/dev/null
    git archive --format tar --worktree-attributes HEAD > ${BUILDDIR}/${PACKAGENAME}.tar
    git rev-parse HEAD > ${BUILDDIR}/version.txt
    pushd $BUILDDIR &>/dev/null
    tar -rf ${PACKAGENAME}.tar version.txt
    gzip -9 ${PACKAGENAME}.tar
    mv ${PACKAGENAME}.tar.gz ${PACKAGENAME}-${version}.tar.gz
    [ -f version.txt ] && rm -f version.txt
    popd &>/dev/null
    popd &>/dev/null

    # Build stage
    local REQUEST=$REQUEST_NUM
    [ -n "$LP_BUG" ] && REQUEST=$LP_BUG

    [ -n "${EXTRAREPO}" ] && EXTRAREPO="${EXTRAREPO}|"
    EXTRAREPO="${EXTRAREPO}repo1,http://${REMOTE_REPO_HOST}/${RPM_OS_REPO_PATH}/x86_64"
    [ "$IS_UPDATES" == 'true' ] && \
      EXTRAREPO="${EXTRAREPO}|repo2,http://${REMOTE_REPO_HOST}/${RPM_PROPOSED_REPO_PATH}/x86_64"
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ "$IS_UPDATES" != "true" ] && [ -n "$LP_BUG" ] && \
      EXTRAREPO="${EXTRAREPO}|repo3,http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${RPM_OS_REPO_PATH}/x86_64"
    [ "$GERRIT_STATUS" == "NEW" ] && [ "$IS_UPDATES" == "true" ] && [ -n "$LP_BUG" ] && \
      EXTRAREPO="${EXTRAREPO}|repo3,http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${RPM_PROPOSED_REPO_PATH}/x86_64"
    export EXTRAREPO

    if [ -n "$EXTRAREPO" ] ; then
        local EXTRAPARAMS=""
        local OLDIFS="$IFS"
        IFS='|'
        for repo in $EXTRAREPO; do
          IFS="$OLDIFS"
          [ -n "$repo" ] && EXTRAPARAMS="${EXTRAPARAMS} --repository ${repo#*,}"
          IFS='|'
        done
        IFS="$OLDIFS"
    fi

    local tmpdir=$(mktemp -d ${PKG_DIR}/build-XXXXXXXX)
    echo "BUILD_SUCCEEDED=false" > ${WRKDIR}/buildresult.params
    bash -c "${WRKDIR}/build \
          --verbose \
          --no-keep-chroot \
          --dist ${DIST} \
          --build \
          --source $BUILDDIR \
          --output $tmpdir \
          ${EXTRAPARAMS}"
    local exitstatus=$(cat ${tmpdir}/exitstatus || echo 1)
    [ -f "${tmpdir}/build.log" ] && mv "${tmpdir}/build.log" "${WRKDIR}/buildlog.txt"
    [ -f "${tmpdir}/root.log" ] && mv "${tmpdir}/root.log" "${WRKDIR}/rootlog.txt"

    fill_buildresult $exitstatus 0 $PACKAGENAME RPM
    if [ "$exitstatus" == "0" ] && [ -n "${GERRIT_BRANCH}" ]; then
        rm -f ${WRKDIR}/buildresult.params
        cat >${WRKDIR}/buildresult.params<<-EOL
			BUILD_HOST=`hostname -f`
			PKG_PATH=$tmpdir
			GERRIT_CHANGE_STATUS=$GERRIT_CHANGE_STATUS
			REQUEST_NUM=$REQUEST_NUM
			LP_BUG=$LP_BUG
			IS_SECURITY=$IS_SECURITY
			EXTRAREPO="$EXTRAREPO"
			REPO_TYPE=rpm
			DIST=$DIST
		EOL
    fi
    echo "Packages: $PACKAGENAME"

    exit $exitstatus
}

main $@

exit 0
