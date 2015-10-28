#!/bin/bash

set -o xtrace
set -o errexit

[ -f ".packages-defaults" ] && source .packages-defaults
source build-functions.sh

main () {
  set_default_params
  # Get package tree from gerrit
  fetch_upstream
  local _srcpath="${MYOUTDIR}/${PACKAGENAME}-src"
  local _specpath=$_srcpath
  local _testspath=$_srcpath
  [ "$IS_OPENSTACK" == "true" ] && _specpath="${MYOUTDIR}/${PACKAGENAME}-spec${SPEC_PREFIX_PATH}" && _testspath="${MYOUTDIR}/${PACKAGENAME}-spec"
  local _debianpath=$_specpath

  if [ -d "${_debianpath}/debian" ] ; then
      # Unpacked sources and specs
      local srcpackagename=`head -1 ${_debianpath}/debian/changelog | cut -d' ' -f1`
      local version=`head -1 ${_debianpath}/debian/changelog | sed 's|^.*(||;s|).*$||' | awk -F "-" '{print $1}'`
      # Get version number from the latest git tag for openstack packages
      local release_tag=${version}
      [ "$IS_OPENSTACK" == "true" ] && release_tag=`git -C $_srcpath describe --abbrev=0`
      # Deal with PyPi versions like 2015.1.0rc1
      # It breaks version comparison
      # Change it to 2015.1.0~rc1
      local convert_version_py="$(dirname $(readlink -e $0))/convert-version.py"
      version=$(python ${convert_version_py} --tag ${release_tag})

      local binpackagenames="`cat ${_debianpath}/debian/control | grep ^Package | cut -d' ' -f 2 | tr '\n' ' '`"
      local epochnumber=`head -1 ${_debianpath}/debian/changelog | grep -o "(.:" | sed 's|(||'`
      local distro=`head -1 ${_debianpath}/debian/changelog | awk -F'[ ;]' '{print $3}'`

      # Get last commit info
      # $message $author $email $cdate $commitsha $lastgitlog
      get_last_commit_info ${_srcpath}

      TAR_NAME="${srcpackagename}_${version}.orig.tar.gz"
      if [ "$IS_OPENSTACK" == "true" ] ; then
          # Get revision number as commit count for src+spec projects
          local _src_commit_count=`git -C $_srcpath rev-list --no-merges origin/${SOURCE_BRANCH} | wc -l`
          local _spec_commit_count=`git -C $_specpath rev-list --no-merges origin/${SPEC_BRANCH} | wc -l`
          local _rev=$(( $_src_commit_count + $_spec_commit_count ))
          [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && _rev=$(( $_rev + 1 ))
          local release="1~u14.04+mos${_rev}"
          [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && release="${release}+git.${gitshasrc}.${gitshaspec}"
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
          # Prepare source tarball
          if [ "$PACKAGENAME" == "murano-apps" -o "$PACKAGENAME" == "rally" ]; then
              git -C $_srcpath archive --format tar.gz -o ${BUILDDIR}/${TAR_NAME} ${release_tag}
          else
              git -C $_srcpath archive --format tar.gz --prefix ${srcpackagename}-${version}/ -o ${BUILDDIR}/${TAR_NAME} ${release_tag}
          fi
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
      else
          # Update changelog
          DEBFULLNAME=$author DEBEMAIL=$email dch -c ${_debianpath}/debian/changelog -a "$commitsha $message"
          # Prepare source tarball
          # Exclude debian and tests dir
          cat > ${_srcpath}/.gitattributes <<-EOF
			/debian export-ignore
			/tests export-ignore
			/.gitignore export-ignore
			/.gitreview export-ignore
			EOF
          git -C ${_srcpath} archive --format tar.gz --worktree-attributes -o ${BUILDDIR}/${TAR_NAME} HEAD
      fi
      mkdir -p ${BUILDDIR}/$srcpackagename
      cp -R ${_debianpath}/debian ${BUILDDIR}/${srcpackagename}/
  else
      # Packed sources (.dsc + .gz )
      cp ${_srcpath}/* $BUILDDIR
  fi
  # Prepare tests folder to provide as parameter
  rm -f ${WRKDIR}/tests.envfile
  [ -d "${_testspath}/tests" ] && echo "TESTS_CONTENT='`tar -cz -C ${_testspath} tests | base64 -w0`'" > ${WRKDIR}/tests.envfile

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

  exit $exitstatus
}

main "$@"

exit 0
