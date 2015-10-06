%define name fuel-createmirror
%{!?version: %define version 8.0.0}
%{!?release: %define release 1}

Name:           %{name}
Version:        %{version}
Release:        %{release}%{?dist}
Summary:        CLI script for MOS/upstream mirroring
URL:            http://mirantis.com

Group:          Development/Tools
License:        GPLv2
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-buildroot
BuildArch:      noarch

Requires: bash
Requires: docker-io
Requires: dpkg-devel
Requires: fuel-dockerctl
Requires: openssl
Requires: python
Requires: rsync

%description
 **fuel-createmirror -- utility for creating local mirrors of MOS and
 upstream OS repositories

%prep
rm -rf %{name}-%{version}
mkdir %{name}-%{version}
tar xzvf %{SOURCE0} -C %{name}-%{version}
rm -rf %{name}-%{version}/{debian,specs}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/%{name}-%{version}
cp -R %{name}-%{version}/* %{buildroot}/opt/%{name}-%{version}
rm -f %{buildroot}/opt/%{name}-%{version}/version.txt

%clean
rm -rf %{buildroot}

%post
ln -sf /opt/%{name}-%{version}/%{name} %{_bindir}
ln -sf /opt/%{name}-%{version}/config %{_sysconfdir}/%{name}

%postun
if [ "$1" = "1" ]; then
    rm -f %{_bindir}/%{name}
    rm -f %{_sysconfdir}/%{name}
    ln -sf /opt/%{name}-%{version}/%{name} %{_bindir}
    ln -sf /opt/%{name}-%{version}/config %{_sysconfdir}/%{name}
else
    rm -f %{_bindir}/%{name}
    rm -f %{_sysconfdir}/%{name}
fi

%files
%defattr(-,root,root)
%dir /opt/%{name}-%{version}/
/opt/%{name}-%{version}/%{name}
/opt/%{name}-%{version}/deb-mirror
/opt/%{name}-%{version}/version
/opt/%{name}-%{version}/util/
%config /opt/%{name}-%{version}/config/
/opt/%{name}-%{version}/LICENSE
/opt/%{name}-%{version}/README.md

%changelog
* Thu Sep 03 2015 Sergey Kulanov <skulanov@mirantis.com>
- Bump to version 8.0

* Thu Aug 13 2015 vparakhin <vparakhin@mirantis.com>
- Switch MOS DEB repos to new format, update configs from fuel-main

* Fri Aug 07 2015 Sergey Kulanov <skulanov@mirantis.com>
- Bump version to 7.0. Update code from upstream

* Fri Jul 24 2015 Alex Schultz <aschultz@mirantis.com>
- Fixing permisions after rsync of pool data

* Thu Jun 11 2015 vparakhin <vparakhin@mirantis.com>
- Add sysfsutils package to requirements

* Fri Jun 5 2015 vparakhin <vparakhin@mirantis.com>
- Fix release ID hardcoded in fuel-createmirror

* Thu Jun 4 2015 vparakhin <vparakhin@mirantis.com>
- Change netboot installer path for partial mirror

* Tue Jun 2 2015 vparakhin <vparakhin@mirantis.com>
- Bypass http proxy while accessing Fuel Master node

* Tue Jun 2 2015 mmosesohn <mmosesohn@mirantis.com>
- Added proxy info to help

* Tue May 12 2015 vparakhin <vparakhin@mirantis.com>
- Added fuel-package-updates integration

* Thu Apr 30 2015 vparakhin <vparakhin@mirantis.com>
- Added instructions on repositories setup in Fuel UI

* Tue Apr 28 2015 vparakhin <vparakhin@mirantis.com>
- Script name changed to fuel-createmirror

* Thu Apr 23 2015 vparakhin <vparakhin@mirantis.com>
- Initial release
