%global modname  pg_replication_activity
%global modname2 pgreplicationactivity

Summary:	A python program to monitor postgres replication activity
Name:		python%{python3_pkgversion}-%{modname}
Version:	0.0.1
Release:	1%{?dist}
License:	GPLv3
Group:		Applications/Databases
Url:		https://github.com/bolcom/%{modname}
Source0:	%{name}-%{version}.tar.gz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot-%(%{__id_u} -n)
BuildArch:	noarch
Requires:       python%{python3_pkgversion}-psycopg2
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools

%description
This programs helps to investigate, troubleshoot and monitor postgres replication
activity of a PostgreSQL replicated cluster. It connects to all instances and displays
information like time drift, replication lag (in MBytes and seconds), replication role,
uptream server, etc.

%prep
%setup -n %{modname}-%{version} -q

%build
%py3_build
mkdir -p $RPM_BUILD_ROOT/%{_mandir}/man1/
gzip docs/man/pg_replication_activity.1

%install
%py3_install
mkdir -p %{buildroot}/%{_mandir}/man1/
cp docs/man/%{modname}.1.gz %{buildroot}/%{_mandir}/man1/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{python3_sitelib}/%{modname}-%{version}-py3.*.egg-info
%{python3_sitelib}/%{modname2}

%package bin
Requires: python%{python3_pkgversion}-%{modname} = %{version}
Requires: python%{python3_pkgversion}-setuptools
Summary:  Binaries for a python program to monitor postgres replication activity

%description bin
This programs helps to investigate, troubleshoot and monitor postgres replication
activity of a PostgreSQL replicated cluster. It connects to all instances and displays
information like time drift, replication lag (in MBytes and seconds), replication role,
uptream server, etc.

%files bin
%{_bindir}/pg_replication_activity
%{_mandir}/man1/%{modname}.1.gz

%changelog
* Wed Jul 25 2018 - Sebastiaan Mannem <smannem@bol.com>
- Initial build of this spec
