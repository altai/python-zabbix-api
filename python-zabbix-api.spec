%global with_doc 0

%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif


Name:             python-zabbix-api
Version:          0.1
Release:          1
Summary:          Zabbix API
License:          GNU LGPL 2.1
Vendor:           Grid Dynamics International, Inc.
URL:              http://www.griddynamics.com/openstack
Group:            Development/Languages/Python

Source0:          %{name}-%{version}.tar.gz
BuildRoot:        %{_tmppath}/%{name}-%{version}-build
BuildRequires:    python-devel python-setuptools make
BuildArch:        noarch
Requires:         python-flask
Requires:         python-flask-sqlalchemy
Requires:         python-flask-mail

Requires:         start-stop-daemon


%description


%prep
%setup -q -n %{name}-%{version}/zabbix
sed -i '/Creating %s/d' zabbix_api.py
sed -i 's/sys.exit.*/raise/' zabbix_api.py

%build
%{__python} setup.py build


%install
%__rm -rf %{buildroot}

%{__python} setup.py install -O1 --skip-build --prefix=%{_prefix} --root=%{buildroot}


%clean
%__rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc README*
%{python_sitelib}/*

%changelog
