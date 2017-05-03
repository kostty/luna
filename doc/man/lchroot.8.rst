=======
lchroot
=======

-----------------------------------------------------------------
wrapper command to easily do chroot to configured Luna's osimages
-----------------------------------------------------------------

:Author: Dmitry Chirikov
:Date:   October 2016
:Manual section: 8

SYNOPSIS
========

**lchroot** *osimage* [ *command* ]

DESCRIPTION
===========

**lchroot** is a small shell script with embed C code.

OPTIONS
=======

*osimage*
    Osimage's name.

*command*
    Command to execute in chroot environment. Optional.

FEATURES
========
**lchroot** mounts */proc*, */sys* and */dev* filesystem into the **osimage** tree.
Additionally it compiles and installs fake_chroot.so library to overwrite uname(2) system call to match the version specified for **osimage**.

FILES
=====

/etc/luna.conf
    Credentials to access to MongoDB.


SEE ALSO
========
lweb(1), ltorrent(1), luna(8), lpower(8)
