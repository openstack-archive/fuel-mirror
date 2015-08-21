#!/bin/bash

cp $BINROOT/config/requirements-deb.txt $apt_altstate

cat >> $apt_altstate/requirements-deb.txt << EOF
linux-image-${UBUNTU_INSTALLER_KERNEL_VERSION}
linux-headers-${UBUNTU_INSTALLER_KERNEL_VERSION}
linux-image-generic-${UBUNTU_KERNEL_FLAVOR}
linux-headers-generic-${UBUNTU_KERNEL_FLAVOR}
EOF

requirements_add_essential_pkgs () {
        # All essential packages are already installed, so ask dpkg for a list
        dpkg-query -W -f='${Package} ${Essential}\n' > /tmp/essential.pkgs
        sed -i /tmp/essential.pkgs -n -e 's/\([^ ]\+\).*yes$/\1/p'
        cat /tmp/essential.pkgs >> $apt_altstate/requirements-deb.txt
}

#apt_altstate=`mktemp -d --suffix="-apt-altstate"`
apt_lists_dir="$apt_altstate/var/lib/apt/lists"
apt_cache_dir="$apt_altstate/var/cache/apt"
null_dpkg_status="$apt_altstate/var/lib/dpkg/status"
apt_alt_etc="$apt_altstate/etc/apt"

mkdir -p "$apt_lists_dir"
mkdir -p "$apt_cache_dir"
mkdir -p "$apt_alt_etc/trusted.gpg.d/"
mkdir -p "$apt_alt_etc/preferences.d/"
mkdir -p "${null_dpkg_status%/*}"
touch "${null_dpkg_status}"
cp -a /usr/share/keyrings/ubuntu*.gpg "$apt_alt_etc/trusted.gpg.d/"

apt_altstate_opts="-o APT::Get::AllowUnauthenticated=1"
apt_altstate_opts="${apt_altstate_opts} -o Dir=${apt_altstate}"
apt_altstate_opts="${apt_altstate_opts} -o Dir::State::Lists=${apt_lists_dir}"
apt_altstate_opts="${apt_altstate_opts} -o Dir::State::status=${null_dpkg_status}"
apt_altstate_opts="${apt_altstate_opts} -o Dir::Cache=${apt_cache_dir}"

if ! source "$(dirname $(readlink -f "${BASH_SOURCE[0]}"))/../config/ubuntu.cfg"; then
	echo "`basename $0`: cannot read config for Ubuntu, please create one!"
	exit 1
fi

for dist in ${DISTs[@]}; do
	echo deb http://${UPSTREAM}/${UPSTREAM_DIR} $dist "${DIST_COMPONENTs[$dist]}" >> ${apt_alt_etc}/sources.list
done

if ! source "$(dirname $(readlink -f "${BASH_SOURCE[0]}"))/../config/mos-ubuntu.cfg"; then
	echo "`basename $0`: cannot read config for MOS Ubuntu, please create one!"
	exit 1
fi

for dist in ${DISTs[@]}; do
	echo deb http://${UPSTREAM}/${UPSTREAM_DIR_HTTP} $dist "${DIST_COMPONENTs[$dist]}" >> ${apt_alt_etc}/sources.list
done

cat <<EOF > ${apt_alt_etc}/preferences
Package: *
Pin: release o=Mirantis
Pin-Priority: 1101

Package: dh-python
Pin: release o=Ubuntu
Pin-Priority: 1199
EOF

if ! apt-get $apt_altstate_opts update; then
	echo "`basename $0`: failed to populate alt apt state!"
	exit 1
fi

requirements_add_essential_pkgs

echo "Processing Fuel dependencies..."

has_apt_errors=''
while read pkg; do
	downloads_list="$apt_altstate/downloads_${pkg}.list"
	if ! apt-get $apt_altstate_opts --print-uris --yes -qq install $pkg >"${downloads_list}" 2>>"$apt_altstate/apt-errors.log"; then
		echo "package $pkg can not be installed" >>$apt_altstate/apt-errors.log
		# run apt-get once more to get a verbose error message
		apt-get $apt_altstate_opts --print-uris --yes install $pkg >>$apt_altstate/apt-errors.log 2>&1 || true
		has_apt_errors='yes'
	fi
	sed -i "${downloads_list}" -n -e "s/^'\([^']\+\)['].*$/\1/p"
done < $apt_altstate/requirements-deb.txt

if [ -n "$has_apt_errors" ]; then
	echo "`basename $0`some packages are not installable" >&2
	cat < $apt_altstate/apt-errors.log >&2
	exit 1
fi

# Prepare list of upstream packages to download
cat $apt_altstate/downloads_*.list | grep -v ${UPSTREAM} | perl -p -e 's/^.*?pool/pool/' | sort -u > $apt_altstate/deb
rm -f $apt_altstate/downloads_*.list

NETBOOT_FILES="linux initrd.gz"
for dload in $NETBOOT_FILES; do
    echo dists/${UBUNTU_RELEASE}-updates/main/installer-${UBUNTU_ARCH}/current/images/${UBUNTU_NETBOOT_FLAVOR}/ubuntu-installer/${UBUNTU_ARCH}/${dload} >> $apt_altstate/netboot.list
    echo NONE NONE dists/${UBUNTU_RELEASE}-updates/main/installer-${UBUNTU_ARCH}/current/images/${UBUNTU_NETBOOT_FLAVOR}/ubuntu-installer/${UBUNTU_ARCH}/${dload} >> $apt_altstate/netboot_md5.list
done

exit 0
