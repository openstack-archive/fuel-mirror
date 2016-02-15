%define name fuel-mirror
%{!?version: %define version 9.0.0}
%{!?fuel_release: %define fuel_release 9.0}
%{!?release: %define release 1}

Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
Summary: Utility to create RPM and DEB mirror
URL:     http://mirantis.com
License: GPLv2
Group: Utilities
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot
Prefix: %{_prefix}
BuildRequires:  git
BuildRequires: python-setuptools
BuildRequires: python-pbr
BuildArch: noarch

Requires:    python
Requires:    python-babel >= 1.3
Requires:    python-cliff >= 1.7.0
Requires:    python-fuelclient >= 7.0.0
Requires:    python-packetary == %{version}
Requires:    python-pbr >= 0.8
Requires:    python-six >= 1.5.2
Requires:    PyYAML >= 3.10
# Workaroud for babel bug
Requires:    pytz


%description
Provides two commands fuel-mirror and fuel-createmirror.
Second one is for backward compatibility with the previous
generation of the utility. These commands could be used
to create local copies of MOS and upstream deb and rpm
repositories.

%package -n   python-packetary
Summary:      Library that allows to build and clone deb and rpm repositories
Group:        Development/Libraries

Requires:    createrepo
Requires:    python
Requires:    python-babel >= 1.3
Requires:    python-bintrees >= 2.0.2
Requires:    python-chardet >= 2.0.1
Requires:    python-cliff >= 1.7.0
Requires:    python-debian >= 0.1.21
Requires:    python-eventlet >= 0.15
Requires:    python-lxml >= 1.1.23
Requires:    python-pbr >= 0.8
Requires:    python-six >= 1.5.2
Requires:    python-stevedore >= 1.1.0
# Workaroud for babel bug
Requires:    pytz

%description -n  python-packetary
Provides object model and API for dealing with deb
and rpm repositories. One can use this framework to
implement operations like building repository
from a set of packages, clone repository, find package
dependencies, mix repositories, pull out a subset of
packages into a separate repository, etc.


%prep
%setup -cq -n %{name}-%{version}

%build

cd %{_builddir}/%{name}-%{version} && python setup.py build
cd %{_builddir}/%{name}-%{version}/contrib/fuel_mirror && python setup.py build

%install
cd %{_builddir}/%{name}-%{version} && python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=%{_builddir}/%{name}-%{version}/INSTALLED_FILES
cd %{_builddir}/%{name}-%{version}/contrib/fuel_mirror && python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=%{_builddir}/%{name}-%{version}/contrib/fuel_mirror/INSTALLED_FILES

mkdir -p %{buildroot}/etc/%{name}
mkdir -p %{buildroot}/etc/pki/fuel-gpg/
mkdir -p %{buildroot}/etc/yum/vars/
mkdir -p %{buildroot}/etc/yum.repos.d/
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/%{name}
install -m 755 %{_builddir}/%{name}-%{version}/contrib/fuel_mirror/scripts/fuel-createmirror %{buildroot}/usr/bin/fuel-createmirror
install -m 755 %{_builddir}/%{name}-%{version}/contrib/fuel_mirror/etc/config.yaml %{buildroot}/etc/%{name}/config.yaml
echo "%{fuel_release}" > %{buildroot}/etc/yum/vars/fuelver
# copy GPG key
install -m 644 contrib/fuel_repo/RPM-GPG-KEY-mos %{buildroot}/etc/pki/fuel-gpg/
# copy yum repos and mirror lists to /etc/yum.repos.d
for file in contrib/fuel_repo/*.repo contrib/fuel_repo/mos-mirrors* ; do
    install -m 644 "$file" %{buildroot}/etc/yum.repos.d
done

%clean
rm -rf $RPM_BUILD_ROOT

%files -f %{_builddir}/%{name}-%{version}/contrib/fuel_mirror/INSTALLED_FILES
%defattr(0755,root,root)
/usr/bin/fuel-createmirror
%attr(0644,root,root) /etc/%{name}/config.yaml


%files -n python-packetary -f %{_builddir}/%{name}-%{version}/INSTALLED_FILES
%defattr(-,root,root)

%package -n fuel-repository

Summary:   Fuel online repositories package
Version:   %{version}
Release:   %{release}
License:   GPLv2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
URL:       http://github.com/Mirantis

%description -n fuel-repository
This packages provides Yum configuration for Fuel online repositories.

%files -n fuel-repository
%defattr(-,root,root)
%config(noreplace) %attr(0644,root,root) /etc/yum/vars/fuelver
%config(noreplace) %attr(0644,root,root) /etc/yum.repos.d/*
%dir /etc/pki/fuel-gpg
/etc/pki/fuel-gpg/*
