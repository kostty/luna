============
lfs_pxelinux
============

--------------------------------------------------------
FUSE filesystem daemon to servicin pxelinux config files
--------------------------------------------------------

:Author: Dmitry Chirikov
:Date:   January 2017
:Manual section: 1

SYNOPSIS
========

**lfs_pxelinux** [-h] [--debug] [--def_file DEF_FILE] [--mount_mount MOUNT_MOUNT] [--pidfile PIDFILE] { *start* | *stop* | *restart* }

DESCRIPTION
===========

**lfs_pxelinux** is a user-space daemon for creating pxelinux files 'on-demand'. It is talking to **lweb** daemon to get files' content.

Pxelinux binary is looking for boot config in following files (http://www.syslinux.org/wiki/index.php/PXELINUX)::

    /mybootdir/pxelinux.cfg/b8945908-d6a6-41a9-611d-74a6ab80b83d
    /mybootdir/pxelinux.cfg/01-88-99-aa-bb-cc-dd
    /mybootdir/pxelinux.cfg/C0A8025B
    /mybootdir/pxelinux.cfg/C0A8025
    /mybootdir/pxelinux.cfg/C0A802
    /mybootdir/pxelinux.cfg/C0A80
    /mybootdir/pxelinux.cfg/C0A8
    /mybootdir/pxelinux.cfg/C0A
    /mybootdir/pxelinux.cfg/C0
    /mybootdir/pxelinux.cfg/C
    /mybootdir/pxelinux.cfg/default

So lfs_pxelinux will create *01-88-99-aa-bb-cc-d*  and *default* (if **--def_file** is defined) files. Lfs_pxelinux will do request to lweb daemon to figure out if MAC-address exists.

OPTIONS
=======

**--help**, **-h**
    Get help.

**--debug**, **-D**
    Do not start as a daemon. Enables debug for FUSE system calls.

**--def_file**, **-d**
    Path to file with the content for ./default file

**--mount_mount**, **-m**
    Mountpoint. For example /tftpboot/pxelinux.cfg

**--pidfile**, **-p**
    File for storing pid of the process. Default is */var/run/luna/lfs_pxelinux.pid*.

**start**
    Start daemon.

**stop**
    Stop daemon.

**restart**
    Restart daemon.

ENVIRONMENT VARIABLES
=====================

    **LFS_DEBUG**
        See **--debug**.

    **LFS_DEFAULT_FILE**
        See **--def_file**.

    **LFS_MOUNTPOINT**
        See **--mount_mount**.

    **LFS_PIDFILE**
        See **--pidfile**.

FILES
=====

templ_nodeboot_syslinux.cfg
    Template to generate boot config in syslinux (pxelinux) format.
/etc/sysconfig/lfs_pxelinux
    File to store environmental variables for systemd unit

SEE ALSO
========
ltorrent(1), lweb(1), luna(8), lpower(8), lchroot(8)
