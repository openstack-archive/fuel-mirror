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

  # Get last commit info
  # $message $author $email $cdate $commitsha $lastgitlog
  get_last_commit_info ${_srcpath}

  # Update specs
  local specfile=`find $_specpath -name *.spec`
  #local binpackagename=`rpm -q $RPMQUERYPARAMS --specfile $specfile --queryformat %{NAME}"\n" | head -1`
  local define_macros=(
      -D 'kernel_module_package_buildreqs kernel-devel'
      -D 'kernel_module_package(n:v:r:s:f:xp:) \
%package -n kmod-%{-n*} \
Summary: %{-n*} kernel module(s) \
Version: %{version} \
Release: %{release} \
%description -n kmod-%{-n*} \
This package provides the %{-n*} kernel modules
' )
  local version=`rpm -q "${define_macros[@]}" --specfile $specfile --queryformat %{VERSION}"\n" | head -1`
  local release=`rpm -q "${define_macros[@]}" --specfile $specfile --queryformat %{RELEASE}"\n" | head -1`
  ## Add changelog section if it doesn't exist
  [ "`cat ${specfile} | grep -c '^%changelog'`" -eq 0 ] && echo "%changelog" >> ${specfile}
  if [ "$IS_OPENSTACK" == "true" ] ; then
      # Get version number from the latest git tag for openstack packages
      local version=`git -C $_srcpath describe --abbrev=0`
      # TODO: Deal with openstack RC tags like 2015.1.0rc1
      # It breaks rpm version comparison.
      # Get revision number as commit count for src+spec projects
      local _src_commit_count=`git -C $_srcpath rev-list --no-merges origin/${SOURCE_BRANCH} | wc -l`
      local _spec_commit_count=`git -C $_specpath rev-list --no-merges origin/${SPEC_BRANCH} | wc -l`
      local _rev=$(( $_src_commit_count + $_spec_commit_count ))
      [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && _rev=$(( $_rev + 1 ))
      local release="mos8.0.${_rev}"
      [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && release="${release}.git.${gitshasrc}.${gitshaspec}"
      local TAR_NAME=${PACKAGENAME}-${version}.tar.gz
      # Update version and changelog
      sed -i "s|Version:.*$|Version: ${version}|" $specfile
      sed -i "/Release/s|%{?dist}.*$|%{?dist}~${release}|" $specfile
      sed -i "s|Source0:.*$|Source0: ${TAR_NAME}|" $specfile
      # Prepare source tarball
      pushd $_srcpath &>/dev/null
      if [ "$PACKAGENAME" == "murano-apps" ]; then
          # Do not perform `setup.py sdist` for murano-apps package
          tar -czf ${BUILDDIR}/$TAR_NAME $EXCLUDES .
      else
          python setup.py --version  # this will download pbr if it's not available
          PBR_VERSION=$version python setup.py sdist -d ${BUILDDIR}/
          mv ${BUILDDIR}/*.gz ${BUILDDIR}/$TAR_NAME || :
      fi
      cp $_specpath/rpm/SOURCES/* ${BUILDDIR}/ &>/dev/null || :
  else
     # TODO: Support unpacked source tree
     # Packed sources (.spec + .gz + stuff)
     # Exclude tests folder
     cp -R ${_srcpath}/* $BUILDDIR
     [ -d "${BUILDDIR}/tests" ] && rm -rf ${BUILDDIR}/tests
  fi
  ## Update changelog
  firstline=1
  if [ ! -z "$lastgitlog" ]; then
    sed -i "/^%changelog/i%newchangelog" ${specfile}
    echo "$lastgitlog" | while read LINE; do
      commitid=`echo "$LINE" | cut -d'|' -f1`
      email=`echo "$LINE" | cut -d'|' -f2`
      author=`echo "$LINE" | cut -d'|' -f3`
      # Get current date to avoid wrong chronological order in %changelog section
      date=`LC_TIME=C date +"%a %b %d %Y"`
      subject=`echo "$LINE" | cut -d'|' -f4`

      [ $firstline == 1 ] && sed -i "/^%changelog/i\* $date $author \<${email}\> \- ${version}-${release}" ${specfile}
      sed -i "/^%changelog/i\- $commitid $subject" ${specfile}
      firstline=0
    done
    sed -i '/^%changelog/i\\' ${specfile}
    sed -i '/^%changelog/d' ${specfile}
    sed -i 's|^%newchangelog|%changelog|' ${specfile}
  fi
  echo "Resulting spec-file:"
  cat ${specfile}
  cp ${specfile} ${BUILDDIR}/
  # Prepare tests folder to provide as parameter
  rm -f ${WRKDIR}/tests.envfile
  [ -d "${_testspath}/tests" ] && echo "TESTS_CONTENT='`tar -cz -C ${_testspath} tests | base64 -w0`'" > ${WRKDIR}/tests.envfile

  # Build stage
  local REQUEST=$REQUEST_NUM
  [ -n "$LP_BUG" ] && REQUEST=$LP_BUG
  EXTRAREPO="repo1,http://${REMOTE_REPO_HOST}/${RPM_OS_REPO_PATH}/x86_64"

  [ "$IS_UPDATES" == 'true' ] && \
    EXTRAREPO="${EXTRAREPO}|repo2,http://${REMOTE_REPO_HOST}/${RPM_PROPOSED_REPO_PATH}/x86_64"
  [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ "$IS_UPDATES" == "false" ] && \
    EXTRAREPO="${EXTRAREPO}|repo3,http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${RPM_OS_REPO_PATH}/x86_64"
  [ "$GERRIT_STATUS" == "NEW" ] && [ "$IS_UPDATES" == "true" ] && \
    EXTRAREPO="${EXTRAREPO}|repo3,http://${REMOTE_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${RPM_PROPOSED_REPO_PATH}/x86_64"
  export EXTRAREPO

  pushd $BUILDDIR &>/dev/null
  echo "BUILD_SUCCEEDED=false" > ${WRKDIR}/buildresult.params
  bash -x ${WRKDIR}/docker-builder/build-rpm-package.sh
  local exitstatus=`cat build/exitstatus.mock || echo 1`
  rm -f build/exitstatus.mock build/state.log
  [ -f "build/build.log" ] && mv build/build.log ${WRKDIR}/buildlog.txt
  [ -f "build/root.log" ] && mv build/root.log ${WRKDIR}/rootlog.txt
  fill_buildresult $exitstatus 0 $PACKAGENAME RPM
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
		REPO_TYPE=rpm
		DIST=$DIST
		EOL
      mv build/* $tmpdir/
  fi
  popd &>/dev/null

  exit $exitstatus
}

main "$@"

exit 0
