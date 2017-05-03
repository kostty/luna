========
ltorrent
========

------------------------------
Luna BitTorrent seeding daemon
------------------------------

:Author: Dmitry Chirikov
:Date:   October 2016
:Manual section: 1

SYNOPSIS
========

**ltorrent** [ *start* | *stop* | *restart* | *reload* ]

DESCRIPTION
===========

**ltorrent** is a BitTorrent client created to fit to Luna and based on *libtorrent*: http://www.libtorrent.org/

OPTIONS
=======

**start**
    Start daemon.

**stop**
    Stop daemon.

**restart**
    Restart daemon.

FILES
=====

/etc/luna.conf
    Credentials to access to MongoDB.
/var/log/luna/ltorrent.log
    Log file.
/run/luna/ltorrent.pid
    PID file.

SEE ALSO
========
lweb(1), luna(8), lpower(8), lchroot(8)
