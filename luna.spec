Name: luna
Version: 1.1
Release: 2%{?dist}

Summary: Luna is a baremetal provisioning tool uses image-based approach
Packager: ClusterVision
License: GNU GPLv3

Source: https://github.com/clustervision/%{name}/archive/v%{version}.tar.gz
URL: https://github.com/clustervision/luna
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}

# ///////////////////////////////////////////////
# INTERNAL LUNA DEFINITION
# ///////////////////////////////////////////////
%define luna_home /opt/luna
%define luna_group luna
%define luna_user luna
%define dracut_dir /usr/lib/dracut/modules.d

# ///////////////////////////////////////////////
# RPMBUILD DEFINITION
# ///////////////////////////////////////////////
# Disable debuginfo package
%define debug_package %{nil}

# ///////////////////////////////////////////////
# BUILD REQUIREMENTS
# ///////////////////////////////////////////////
BuildRequires: bash
BuildRequires: sed
BuildRequires: python
BuildRequires: python-docutils
BuildRequires: gcc-c++
BuildRequires: rb_libtorrent-devel
BuildRequires: boost-devel

# ///////////////////////////////////////////////
# INSTALL REQUIREMENTS
# ///////////////////////////////////////////////
Requires: nginx
Requires: mongodb-server >= 2.6, mongodb-server < 3.0
Requires: python-pymongo >= 2.5, python-pymongo < 3.0
Requires: mongodb >= 2.6, mongodb < 3.0
Requires: python-tornado >= 2.2, python-tornado < 3.0
Requires: ipxe-bootimgs
Requires: tftp-server
Requires: xinetd
Requires: dhcp
Requires: rb_libtorrent-python
Requires: net-snmp-python
Requires: python-hostlist
Requires: bind-chroot
Requires: python2-llfuse
Requires: python-requests

Requires(pre):   /usr/sbin/useradd,/usr/sbin/userdel
Requires(pre):  /usr/bin/systemctl

Requires(post):  /usr/bin/sed
Requires(post):  /usr/bin/systemctl
Requires(post):  /usr/sbin/groupadd,/usr/sbin/groupdel
Requires(post):  /usr/bin/chmod,/usr/bin/chown
Requires(post):  /usr/bin/getent,/usr/bin/id

Requires(preun): /usr/bin/systemctl

# ///////////////////////////////////////////////
# DESCRIPTION
# ///////////////////////////////////////////////
%description
Luna is a baremetal provisioning tool uses image-based-approach. It delivers image of operating systems, but not the 'recipe' how to configure OS, as competotors do. It dramatically speeds up imstallation time, and reduce administrative efforts.

# ///////////////////////////////////////////////
# CLIENT PACKAGE
# ///////////////////////////////////////////////
%package client
Summary: Kernel module Luna for deployed nodes.
Requires: kernel
Requires: rootfiles
Requires: openssh-server
Requires: openssh
Requires: openssh-clients
Requires: tar
Requires: nc
Requires: wget
Requires: curl
Requires: rsync
Requires: gawk
Requires: sed
Requires: gzip
Requires: parted
Requires: e2fsprogs
Requires: ipmitool
Requires: vim-minimal
Requires: grub2
Requires: rb_libtorrent
Requires: dracut-config-generic

%description client
Dracut module for Luna deployment tool

# ///////////////////////////////////////////////
# PREPARATION SECTION
# ///////////////////////////////////////////////
%prep
%setup -n %{name}-%{version}

# ///////////////////////////////////////////////
# BUILD SECTION
# ///////////////////////////////////////////////
%build
pushd doc/man
make
popd
pushd contrib/ltorrent-client/
make
popd

# ///////////////////////////////////////////////
# INSTALL SECTION
# ///////////////////////////////////////////////
%install
# Install files for main package
# Main module
%{__install} -m 755 -d luna                                     %{buildroot}%{python_sitelib}/luna
%{__install} -m 755 -d luna/utils                               %{buildroot}%{python_sitelib}/luna/utils
for f in luna/*.py luna/utils/*.py; do
    %{__install} -m 644 $f                                      %{buildroot}%{python_sitelib}/$f
done
pushd bin
for f in *; do
    %{__install} -m 755 -D $f                                   %{buildroot}%{_sbindir}/$f
done
popd
# Config file
%{__install} -m 644 -D contrib/luna.conf                        %{buildroot}%{_sysconfdir}/luna.conf
# Man files
%{__install} -m 644 -D doc/man/lchroot.8.gz                     %{buildroot}%{_mandir}/man8/lchroot.8.gz
%{__install} -m 644 -D doc/man/lfs_pxelinux.1.gz                %{buildroot}%{_mandir}/man1/lfs_pxelinux.1.gz
%{__install} -m 644 -D doc/man/lpower.8.gz                      %{buildroot}%{_mandir}/man8/lpower.8.gz
%{__install} -m 644 -D doc/man/ltorrent.1.gz                    %{buildroot}%{_mandir}/man1/ltorrent.1.gz
%{__install} -m 644 -D doc/man/luna.8.gz                        %{buildroot}%{_mandir}/man8/luna.8.gz
%{__install} -m 644 -D doc/man/lweb.1.gz                        %{buildroot}%{_mandir}/man1/lweb.1.gz
# Other docs
%{__install} -m 644 -D LICENSE                                  %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/LICENSE
%{__install} -m 644 -D README.md                                %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/README.md
%{__install} -m 644 -D doc/man/lchroot.8.rst                    %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/doc/lchroot.rst
%{__install} -m 644 -D doc/man/lfs_pxelinux.1.rst               %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/doc/lfs_pxelinux.rst
%{__install} -m 644 -D doc/man/lpower.8.rst                     %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/doc/lpower.rst
%{__install} -m 644 -D doc/man/ltorrent.1.rst                   %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/doc/ltorrent.rst
%{__install} -m 644 -D doc/man/luna.8.rst                       %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/doc/luna.rst
%{__install} -m 644 -D doc/man/lweb.1.rst                       %{buildroot}%{_defaultdocdir}/%{name}-%{version}-%{release}/doc/lweb.rst
# Systemd unit files
%{__install} -m 644 -D contrib/systemd/lweb.service             %{buildroot}%{_unitdir}/lweb.service
%{__install} -m 644 -D contrib/systemd/ltorrent.service         %{buildroot}%{_unitdir}/ltorrent.service
%{__install} -m 644 -D contrib/systemd/lfs_pxelinux             %{buildroot}%{_sysconfdir}/sysconfig/lfs_pxelinux
%{__install} -m 644 -D contrib/systemd/lfs_pxelinux.service     %{buildroot}%{_unitdir}/lfs_pxelinux.service
# Bash autocomplete
%{__install} -m 644 -D contrib/luna_autocomplete.sh             %{buildroot}%{_sysconfdir}/profile.d/luna_autocomplete.sh
# Create luna system directories
%{__mkdir_p}                                                    %{buildroot}%{_var}/log/luna
# Example config
%{__install} -m 644 -D contrib/nginx/luna.conf                  %{buildroot}%{_datarootdir}/luna/nginx-luna.conf
# Templates
%{__install} -m 755 -d templates                                %{buildroot}%{_datarootdir}/luna/templates
for f in templates/*; do
    %{__install} -m 644 -D $f                                   %{buildroot}%{_datarootdir}/luna/$f
done

# client files
%{__install} -m 755 -d contrib/dracut/95luna                    %{buildroot}%{dracut_dir}/95luna
pushd contrib/dracut
for f in 95luna/*; do
    %{__install} -m 644 -D $f                                   %{buildroot}%{dracut_dir}/$f
done
popd
%{__install} -m 644 -D contrib/ltorrent-client/ltorrent-client  %{buildroot}%{dracut_dir}/95luna/ltorrent-client

# ///////////////////////////////////////////////
# CLEAN SECTION
# ///////////////////////////////////////////////
%clean
rm -rf %{buildroot}

# ///////////////////////////////////////////////
# PRE INSTALLATION PHASE
# ///////////////////////////////////////////////
%pre
case "$1" in
    # This is an initial install.
    1)
        # Stop services
        /usr/bin/systemctl stop lweb ltorrent 2>/dev/null || /usr/bin/true
        # Remove user
        /usr/sbin/groupadd -r %{luna_group} 2>/dev/null || /usr/bin/true
        /usr/sbin/useradd -r -g %{luna_group} -d %{luna_home} %{luna_user} 2>/dev/null || /usr/bin/true
    ;;

    # This is an upgrade.
    2)
        # Stop services
        /usr/bin/systemctl stop lweb ltorrent 2>/dev/null || /usr/bin/true
    ;;
esac
exit 0

# ///////////////////////////////////////////////
# POST INSTALLATION PHASE
# ///////////////////////////////////////////////
%post
LUNA_HOME_DIR=$(eval echo ~%{luna_user})
%{__mkdir_p} ${LUNA_HOME_DIR}/boot
%{__mkdir_p} ${LUNA_HOME_DIR}/torrents
if [ ! -d ${LUNA_HOME_DIR}/templates ]; then
    %{__cp} -pr %{_datarootdir}/luna/templates ${LUNA_HOME_DIR}/
else
    (>&2 echo "Warning: ${LUNA_HOME_DIR}/templates exists. Please copy %{_datarootdir}/luna/templates to ${LUNA_HOME_DIR} manually")
fi
%{__chown} -R %{luna_user}:%{luna_group} ${LUNA_HOME_DIR}
exit 0

# ///////////////////////////////////////////////
# PRE REMOVE PHASE
# ///////////////////////////////////////////////
%preun
case "$1" in
    # This is an un-installation (0) or an upgrade (1).
    [0-1])
        # Stop luna services
        /usr/bin/systemctl stop lweb ltorrent 2>/dev/null || /usr/bin/true
    ;;
esac
exit 0

# ///////////////////////////////////////////////
# POST REMOVE PHASE
# ///////////////////////////////////////////////
%postun
case "$1" in
    # This is an un-installation (0) or an upgrade (1).
    [0-1])
        # Reload systemd config.
        /usr/sbin/userdel luna
        /usr/bin/systemctl daemon-reload
    ;;
esac
exit 0

# ///////////////////////////////////////////////
# LIST FILES SECTION
# ///////////////////////////////////////////////
%files
%defattr(-, root, root)
%config(noreplace) %attr(0600, %{luna_user}, %{luna_group}) %{_sysconfdir}/luna.conf
%{_sbindir}/*
%{python_sitelib}/luna*
%doc %{_mandir}/man1/*
%doc %{_mandir}/man8/*
%doc %{_defaultdocdir}/%{name}-%{version}-%{release}
%{_unitdir}/*
%{_sysconfdir}/sysconfig/lfs_pxelinux
%{_sysconfdir}/profile.d/luna_autocomplete.sh
%config(noreplace) %attr(0700, %{luna_user}, %{luna_group}) %{_var}/log/luna
%{_datarootdir}/luna

%files client
%defattr(-,root,root)
%attr(0755, root, root) %{dracut_dir}/95luna

# ///////////////////////////////////////////////
# CHANGELOG
# ///////////////////////////////////////////////
%changelog
 * Thu Feb 16 2017 Cedric Castagnede <cedric.castagnede@clustervision.com> 1.0
 - First version of this spec file.
 * Tue Feb 21 2017 Dmitry Chirikov <dmitry@chirikov.ru> 1.1
 - Cleanup
 - Migrating to 1.1
 - Using RPM's macroses
