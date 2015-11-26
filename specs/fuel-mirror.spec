%define name python-fuel-mirror
%{!?version: %define version 0.1.0}
%{!?release: %define release 1}

Summary: Fuel-Mirror package
Name: %{name}
Obsoletes: fuel-createmirror
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: Apache
Group: Development/Libraries
URL:       http://github.com/Mirantis
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot
Prefix: %{_prefix}
BuildRequires   python-pbr >= 0.8
BuildRequires:  python-setuptools
BuildRequires:  git
BuildArch:      noarch

Requires:    python-babel >= 1.3
Requires:    python-cliff >= 1.7.0
Requires:    python-fuelclient >= 7.0.0
Requires:    python-packetary >= %{version}
Requires:    python-pbr >= 0.8
Requires:    python-six >= 1.5.2
Requires:    python-setuptools
Requires:    PyYAML >= 3.10
# Workaroud for babel bug
Requires:    pytz

%description
Fuel-Mirror package

%prep
%setup -cq -n %{name}-%{version}

%build

cd %{_builddir}/%{name}-%{version} && python setup.py build
cd %{_builddir}/%{name}-%{version}/contrib/fuel_mirror && python setup.py build

%install
cd %{_builddir}/%{name}-%{version} && python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=%{_builddir}/%{name}-%{version}/INSTALLED_FILES
cd %{_builddir}/%{name}-%{version}/contrib/fuel_mirror && python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=%{_builddir}/%{name}-%{version}/contrib/fuel_mirror/INSTALLED_FILES

mkdir -p %{buildroot}/etc/fuel-mirror
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/fuel-mirror
install -m 755 %{_builddir}/%{name}-%{version}/contrib/fuel_mirror/scripts/fuel-createmirror %{buildroot}/usr/bin/fuel-createmirror

%clean
rm -rf $RPM_BUILD_ROOT

%files -f %{_builddir}/%{name}-%{version}/contrib/fuel_mirror/INSTALLED_FILES
%defattr(0755,root,root)
/usr/bin/fuel-createmirror

%package -n python-packetary
Summary:   The Packetary Package
Version:   %{version}
Release:   %{release}
License:   Apache
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
URL:       http://github.com/Mirantis

BuildRequires:  python-setuptools
BuildRequires:  git
BuildArch:      noarch

Requires:    createrepo
Requires:    python-babel >= 1.3
Requires:    python-bintrees >= 2.0.2
Requires:    python-chardet >= 2.0.1
Requires:    python-cliff >= 1.7.0
Requires:    python-debian >= 1.1.23
Requires:    python-eventlet >= 0.15
Requires:    python-lxml >= 1.1.23
Requires:    python-pbr >= 0.8
Requires:    python-six >= 1.5.2
Requires:    python-setuptools
Requires:    python-stevedore >= 1.1.0
# Workaroud for babel bug
Requires:    pytz


%description -n python-packetary
The chain of tools to manage package`s lifecycle.

%files -n python-packetary -f %{_builddir}/%{name}-%{version}/INSTALLED_FILES
%defattr(-,root,root)
