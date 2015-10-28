#!/bin/bash

set -o xtrace
set -o errexit

[ -f .fuel-default ] && source .fuel-default
source $(dirname `readlink -e $0`)/build-functions.sh

main () {
    set_default_params
    [ -n "$GERRIT_BRANCH" ] && SOURCE_BRANCH=$GERRIT_BRANCH && SOURCE_REFSPEC=$GERRIT_REFSPEC
    [ -n "$GERRIT_PROJECT" ] && SRC_PROJECT=$GERRIT_PROJECT
    PACKAGENAME=${SRC_PROJECT##*/}
    local DEBSPECFILES="${PACKAGENAME}-src/debian"
    # Get package tree from gerrit
    fetch_upstream

    local _srcpath="${MYOUTDIR}/${PACKAGENAME}-src"
    local _specpath=$_srcpath
    local _debianpath=$_specpath

    if [ -d "${_debianpath}/debian" ] ; then
        # Unpacked sources and specs
        local srcpackagename=`head -1 ${_debianpath}/debian/changelog | cut -d' ' -f1`
        local version=`head -1 ${_debianpath}/debian/changelog | sed 's|^.*(||;s|).*$||' | awk -F "-" '{print $1}'`
        local release_tag=`git -C $_srcpath describe --abbrev=0 --always`
        local binpackagenames="`cat ${_debianpath}/debian/control | grep ^Package | cut -d' ' -f 2 | tr '\n' ' '`"
        local epochnumber=`head -1 ${_debianpath}/debian/changelog | grep -o "(.:" | sed 's|(||'`
        local distro=`head -1 ${_debianpath}/debian/changelog | awk -F'[ ;]' '{print $3}'`

        # Get last commit info
        # $message $author $email $cdate $commitsha $lastgitlog
        get_last_commit_info ${_srcpath}

        # Get revision number as commit count for src+spec projects
        local _rev=`git -C $_srcpath rev-list --no-merges origin/${SOURCE_BRANCH} | wc -l`
        [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && _rev=$(( $_rev + 1 ))

        if [ "$version" != "${release_tag}" ] ; then
            local commit_date=$(date --date="${cdate}" +"%Y%m%d")
            version=${version}~git${commit_date}+${_rev}
            release_tag=HEAD
        fi

        local release="1~u14.04+mos${_rev}"
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

        TAR_NAME="${srcpackagename}_${version}.orig.tar.gz"
        # Update changelog
        DEBFULLNAME=$author DEBEMAIL=$email dch -c ${_debianpath}/debian/changelog -a "$commitsha $message"
        # Prepare source tarball
        # Exclude debian dir
        cat > ${_srcpath}/.gitattributes <<-EOF
			/debian export-ignore
			/.gitignore export-ignore
			/.gitreview export-ignore
			EOF
        git -C ${_srcpath} archive --format tar.gz --worktree-attributes -o ${BUILDDIR}/${TAR_NAME} ${release_tag}
        # Prepare patch-file
        if [ $(git -C $_srcpath diff --name-only ${release_tag}..HEAD | wc -l) -gt 0 ] ; then
            local _patches=${_debianpath}/debian/patches
            local _series=${_patches}/series
            local _patchfile="HEAD-${gitshasrc}.patch"
            [ ! -d "${_patches}" ] && mkdir -p ${_patches}
            if [ ! -f "${_series}" ] ; then
                echo "${_patchfile}" > ${_series}
            else
                sed -e "1i${_patchfile}" -i ${_series}
            fi
            git -C $_srcpath diff -p ${release_tag}..HEAD > ${_patches}/${_patchfile}
        fi

        mkdir -p ${BUILDDIR}/$srcpackagename
        cp -R ${_debianpath}/debian ${BUILDDIR}/${srcpackagename}/
    fi

    # Build stage
    local REQUEST=$REQUEST_NUM
    [ -n "$LP_BUG" ] && REQUEST=$LP_BUG

    COMPONENTS="main restricted"
    EXTRAREPO="http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_DIST_NAME} ${COMPONENTS}"
    [ "$IS_UPDATES" == 'true' ] \
        && EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_PROPOSED_DIST_NAME} ${COMPONENTS}"
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ "$IS_UPDATES" == "false" ] \
        && EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${DEB_REPO_PATH} ${DEB_DIST_NAME} ${COMPONENTS}"
    [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ "$IS_UPDATES" == "true" ] \
        && EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${DEB_REPO_PATH} ${DEB_PROPOSED_DIST_NAME} ${COMPONENTS}"
    export EXTRAREPO

    pushd $BUILDDIR &>/dev/null
    echo "BUILD_SUCCEEDED=false" > ${WRKDIR}/buildresult.params
    bash -ex ${WRKDIR}/docker-builder/build-deb-package.sh
    local exitstatus=`cat buildresult/exitstatus.sbuild || echo 1`
    rm -f buildresult/exitstatus.sbuild
    [ -f "buildresult/buildlog.sbuild" ] && mv buildresult/buildlog.sbuild ${WRKDIR}/buildlog.txt
    fill_buildresult $exitstatus 0 $PACKAGENAME DEB
    if [ "$exitstatus" == "0" ] ; then
        tmpdir=`mktemp -d ${PKG_DIR}/build-XXXXXXXX`
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
        mv buildresult/* $tmpdir/
    fi
    popd &>/dev/null
    echo "Packages: $PACKAGENAME"

    exit $exitstatus
}

main $@

exit 0
