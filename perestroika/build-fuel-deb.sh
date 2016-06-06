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
    local DEBSPECFILES="${PACKAGENAME}-src/debian"

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

    local _specpath=$_srcpath
    local _debianpath=$_specpath

    if [ -d "${_debianpath}/debian" ] ; then
        # Unpacked sources and specs
        local srcpackagename=`head -1 ${_debianpath}/debian/changelog | cut -d' ' -f1`
        local version=`head -1 ${_debianpath}/debian/changelog | sed 's|^.*(||;s|).*$||' | awk -F "-" '{print $1}'`
        local binpackagenames="`cat ${_debianpath}/debian/control | grep ^Package | cut -d' ' -f 2 | tr '\n' ' '`"
        local epochnumber=`head -1 ${_debianpath}/debian/changelog | grep -o "(.:" | sed 's|(||'`
        local distro=`head -1 ${_debianpath}/debian/changelog | awk -F'[ ;]' '{print $3}'`

        # Get last commit info
        # $message $author $email $cdate $commitsha $lastgitlog
        get_last_commit_info ${_srcpath}

        # Get revision number as commit count for src+spec projects
        local _rev=`git -C $_srcpath rev-list --no-merges origin/${SOURCE_BRANCH} | wc -l`
        [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && _rev=$(( $_rev + 1 ))
        local release="1~u14.04+mos${_rev}"
        # if gitshasrc is not defined (we are not using fetch_upstream), let's do it
        [ -n "${gitshasrc}" ] || local gitshasrc=$(git -C $_srcpath log -1 --pretty="%h")
        [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && release="${release}+git.${gitshasrc}"
        local fullver=${epochnumber}${version}-${release}
        # Update version and changelog
        local firstline=1
        local _dchopts="-c ${_debianpath}/debian/changelog"
        echo "$lastgitlog" | while read LINE; do
            [ $firstline == 1 ] && local cmd="dch $_dchopts -D $distro -b --force-distribution -v $fullver" || local cmd="dch $_dchopts -a"
            firstline=0
            local commitid=`echo "$LINE" | cut -d'|' -f1`
            local email=`echo "$LINE" | cut -d'|' -f2`
            local author=`echo "$LINE" | cut -d'|' -f3`
            local subject=`echo "$LINE" | cut -d'|' -f4`
            DEBFULLNAME="$author" DEBEMAIL="$email" $cmd "$commitid $subject"
        done

        TAR_NAME="${srcpackagename}_${version#*:}.orig.tar.gz"
        # Update changelog
        DEBFULLNAME=$author DEBEMAIL=$email dch -c ${_debianpath}/debian/changelog -a "$commitsha $message"
        # Prepare source tarball
        # Exclude debian dir
        pushd $_srcpath &>/dev/null
            cat >.gitattributes<<-EOF
				/debian export-ignore
				/.gitignore export-ignore
				/.gitreview export-ignore
			EOF
            git archive --prefix=./ --format=tar.gz --worktree-attributes HEAD --output="${BUILDDIR}/${TAR_NAME}"
        popd &>/dev/null

        mkdir -p ${BUILDDIR}/$srcpackagename
        cp -R ${_debianpath}/debian ${BUILDDIR}/${srcpackagename}/
    fi

    # Build stage
    local REQUEST=$REQUEST_NUM
    [ -n "$LP_BUG" ] && REQUEST=$LP_BUG

    COMPONENTS="main restricted"
    [ -n "${EXTRAREPO}" ] && EXTRAREPO="${EXTRAREPO}|"
    EXTRAREPO="${EXTRAREPO}http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_DIST_NAME} ${COMPONENTS}"
    [ "$IS_UPDATES" == 'true' ] \
        && EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_PROPOSED_DIST_NAME} ${COMPONENTS}"
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ "$IS_UPDATES" != "true" ] && [ -n "$LP_BUG" ] \
        && EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${DEB_REPO_PATH} ${DEB_DIST_NAME} ${COMPONENTS}"
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ "$IS_UPDATES" == "true" ] && [ -n "$LP_BUG" ] \
        && EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${DEB_REPO_PATH} ${DEB_PROPOSED_DIST_NAME} ${COMPONENTS}"
    export EXTRAREPO

    if [ -n "$EXTRAREPO" ] ; then
        local EXTRAPARAMS=""
        local OLDIFS="$IFS"
        IFS='|'
        for repo in $EXTRAREPO; do
            IFS="$OLDIFS"
            [ -n "$repo" ] && EXTRAPARAMS="${EXTRAPARAMS} --repository \"$repo\""
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
    [ -f "${tmpdir}/buildlog.sbuild" ] && mv "${tmpdir}/buildlog.sbuild" "${WRKDIR}/buildlog.txt"

    fill_buildresult $exitstatus 0 $PACKAGENAME DEB
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
			REPO_TYPE=deb
			DIST=$DIST
		EOL
    fi
    echo "Packages: $PACKAGENAME"

    exit $exitstatus
}

main $@

exit 0
