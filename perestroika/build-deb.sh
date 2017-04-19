#!/bin/bash

set -o xtrace
set -o errexit

[ -f ".packages-defaults" ] && source .packages-defaults
BINDIR=$(dirname `readlink -e $0`)
source "${BINDIR}"/build-functions.sh

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
      local binpackagenames="`cat ${_debianpath}/debian/control | grep ^Package | cut -d' ' -f 2 | tr '\n' ' '`"
      local epochnumber=`head -1 ${_debianpath}/debian/changelog | grep -o "(.:" | sed 's|(||'`
      local distro=`head -1 ${_debianpath}/debian/changelog | awk -F'[ ;]' '{print $3}'`

      # Get last commit info
      # $message $author $email $cdate $commitsha $lastgitlog
      get_last_commit_info ${_srcpath}

      TAR_NAME="${srcpackagename}_${version#*:}.orig.tar.gz"
      if [ "$IS_OPENSTACK" == "true" ] ; then
          # Get version number from the latest git tag for openstack packages
          local release_tag=$(git -C $_srcpath describe --abbrev=0 --candidates=1 --match "*[0-9]*")
          # Deal with PyPi versions like 2015.1.0rc1
          # It breaks version comparison
          # Change it to 2015.1.0~rc1
          local convert_version_py="$(dirname $(readlink -e $0))/convert_version.py"
          version=$(python ${convert_version_py} --tag ${release_tag})
          # Get revision number as commit count from tag to head of source branch
          if [ "$IS_PLUGIN" = "true" ]
          then
              local _rev=$(git -C $_srcpath rev-list ${release_tag}..origin/${SOURCE_BRANCH} | wc -l)
          else
              local _rev=$(git -C $_srcpath rev-list --no-merges ${release_tag}..origin/${SOURCE_BRANCH} | wc -l)
          fi
          [ "$GERRIT_CHANGE_STATUS" == "NEW" ] \
              && [ ${GERRIT_PROJECT} == "${SRC_PROJECT}" ] \
              && _rev=$(( $_rev + 1 ))
          [ "$IS_HOTFIX" == "true" ] \
              && _rev=$(get_extra_revision hotfix ${_srcpath} ${release_tag})
          [ "$IS_SECURITY" == "true" ] \
              && _rev=$(get_extra_revision security ${_srcpath} ${release_tag})
          if [ "$IS_PLUGIN" = "true" ]
          then
              version=${version}.dev${_rev}
              local release=$(dpkg-parsechangelog --show-field Version -l${_debianpath}/debian/changelog | awk -F'-' '{print $NF}')
              local ditribution_string=$(dpkg-parsechangelog --show-field Distribution -l${_debianpath}/debian/changelog)
          else
              local release=$(dpkg-parsechangelog --show-field Version -l${_debianpath}/debian/changelog | awk -F'-' '{print $NF}' | sed -r 's|[0-9]+$||')
              local release="${release}${_rev}"
          fi
          local fullver=${epochnumber}${version}-${release}
          local TAR_NAME="${srcpackagename}_${version}.orig.tar.gz"
          # Update version and changelog
          local firstline=1
          local _dchopts="-c ${_debianpath}/debian/changelog"
          echo "$lastgitlog" | while read LINE; do
              [ $firstline == 1 ] && local cmd="dch $_dchopts -D ${ditribution_string:-$distro} -b --force-distribution -v $fullver" || local cmd="dch $_dchopts -a"
              firstline=0
              local commitid=`echo "$LINE" | cut -d'|' -f1`
              local email=`echo "$LINE" | cut -d'|' -f2`
              local author=`echo "$LINE" | cut -d'|' -f3`
              local subject=`echo "$LINE" | cut -d'|' -f4`
              DEBFULLNAME="$author" DEBEMAIL="$email" $cmd "$commitid $subject"
          done
          # Prepare source tarball
          pushd $_srcpath &>/dev/null
          local ignore_list="rally horizon-vendor-theme"
          if [ "$IS_PLUGIN" = "true" ]
          then
              git -C ${_srcpath} archive --format tar.gz \
                  --prefix "${srcpackagename}-${version}/" \
                  --worktree-attributes -o ${BUILDDIR}/${TAR_NAME} HEAD
          elif [ $(echo $ignore_list | grep -Eo "(^| )$PACKAGENAME( |$)") ]; then
              # Do not perform `setup.py sdist` for rally packages
              tar -czf ${BUILDDIR}/$TAR_NAME $EXCLUDES .
          else
              # Use virtualenv to deal with different pbr requirements
              local venv=$(mktemp -d)
              virtualenv "$venv"
              source "${venv}/bin/activate"
              pip install --upgrade setuptools
              python setup.py --version  # this will download pbr if it's not available
              PBR_VERSION=$release_tag python setup.py sdist -d ${BUILDDIR}/
              deactivate
              [ -d "$venv" ] && rm -rf "$venv"
              # Fix source folder name at sdist tarball
              local sdist_tarball=$(find ${BUILDDIR}/ -maxdepth 1 -name "*.gz")
              if [ "$(tar -tf $sdist_tarball | head -n 1 | cut -d'/' -f1)" != "${srcpackagename}-${version}" ] ; then
                  # rename source folder
                  local tempdir=$(mktemp -d)
                  tar -C $tempdir -xf $sdist_tarball
                  mv $tempdir/* $tempdir/${srcpackagename}-${version}
                  tar -C $tempdir -czf ${BUILDDIR}/$TAR_NAME ${srcpackagename}-${version}
                  rm -f $sdist_tarball
                  [ -d "$tempdir" ] && rm -rf $tempdir
              else
                  mv $sdist_tarball ${BUILDDIR}/$TAR_NAME || :
              fi
          fi
          popd &>/dev/null
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
  DEB_HOTFIX_DIST_NAME=${DEB_HOTFIX_DIST_NAME:-hotfix}
  [ -n "${EXTRAREPO}" ] && EXTRAREPO="${EXTRAREPO}|"
  EXTRAREPO="${EXTRAREPO}http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_DIST_NAME} ${COMPONENTS}"
  case true in
      "$IS_HOTFIX" )
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_HOTFIX_DIST_NAME} ${COMPONENTS}"
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_UPDATES_DIST_NAME} ${COMPONENTS}"
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_SECURITY_DIST_NAME} ${COMPONENTS}"
          ;;
      "$IS_SECURITY" )
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_UPDATES_DIST_NAME} ${COMPONENTS}"
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_SECURITY_DIST_NAME} ${COMPONENTS}"
          ;;
      "$IS_UPDATES" )
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_PROPOSED_DIST_NAME} ${COMPONENTS}"
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_UPDATES_DIST_NAME} ${COMPONENTS}"
          EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REPO_HOST}/${DEB_REPO_PATH} ${DEB_SECURITY_DIST_NAME} ${COMPONENTS}"
          ;;
  esac

  if [ "$GERRIT_CHANGE_STATUS" == "NEW" ] && [ -n "$LP_BUG" -o -n "$CUSTOM_REPO_ID" ] ; then
      local DEB_REQUEST_REPO_PATH=${DEB_REQUEST_REPO_PATH:-$DEB_REPO_PATH}
      local REMOTE_REQUEST_REPO_HOST=${REMOTE_REQUEST_REPO_HOST:-$REMOTE_REPO_HOST}
      case true in
          "$IS_HOTFIX" )
              local DEB_REQUEST_DIST_NAME=$DEB_HOTFIX_DIST_NAME
              ;;
          "$IS_SECURITY" )
              local DEB_REQUEST_DIST_NAME=$DEB_SECURITY_DIST_NAME
              ;;
          "$IS_UPDATES" )
              local DEB_REQUEST_DIST_NAME=$DEB_PROPOSED_DIST_NAME
              ;;
          *)
              local DEB_REQUEST_DIST_NAME=$DEB_DIST_NAME
              ;;
      esac
      EXTRAREPO="${EXTRAREPO}|http://${REMOTE_REQUEST_REPO_HOST}/${REPO_REQUEST_PATH_PREFIX}/${REQUEST}/${DEB_REQUEST_REPO_PATH} ${DEB_REQUEST_DIST_NAME} ${COMPONENTS}"
  fi

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
  if [ "$exitstatus" == "0" ] ; then
      rm -f ${WRKDIR}/buildresult.params
      cat >${WRKDIR}/buildresult.params<<-EOL
		BUILD_HOST=`hostname -f`
		PKG_PATH=$tmpdir
		GERRIT_CHANGE_STATUS=$GERRIT_CHANGE_STATUS
		REQUEST_NUM=$REQUEST_NUM
		LP_BUG=$LP_BUG
		IS_SECURITY=$IS_SECURITY
		IS_HOTFIX=$IS_HOTFIX
		EXTRAREPO="$EXTRAREPO"
		REPO_TYPE=deb
		DIST=$DIST
		EOL
  fi

  exit $exitstatus
}

main "$@"

exit 0
