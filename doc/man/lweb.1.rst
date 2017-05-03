====
lweb
====

-------------------------------------------------------------
Luna daemon which provides boot and install scripts for nodes
-------------------------------------------------------------

:Author: Dmitry Chirikov
:Date:   October 2016
:Manual section: 1

SYNOPSIS
========

**lweb** [ *start* | *stop* | *restart*]

DESCRIPTION
===========

**lweb** is a daemon nodes can talk with, and request script for different "steps" of the install process. By default **lweb**  binds to 127.0.0.1:7050 on install server. HTTP reverse proxy (Nginx) is used to provide access from the network.
**lweb** is also running a background process to scan all configured switches to acquire all learned mac addresses and store it in cache.

OPTIONS
=======

**start**
    Start daemon.

**stop**
    Stop daemon.

**restart**
    Restart daemon.

STEPS
=====
**lweb** daemon is stateless. It means it does not aware what was the previous state of the node. So some additional parameters might be required from the node.

*boot*
    Generates reply based on *templ_ipxe.cfg*. Example::

        curl "http://localhost:7050/luna?step=boot"

*discovery*
    Generates reply based on *templ_nodeboot.cfg*. Node sends its data (all MAC addresses) to identify itself. **lweb** is trying to find that data in cache. Example::

        curl "http://localhost:7050/luna?step=discovery&hwdata=|7c%3Ad3%3A0a%3Ab1%3A89%3Ab8|"


*install*
    Generates reply based on *templ_install.cfg*. Example::

        curl "http://localhost:7050/luna?step=install&node=node001"

FILES
=====

/etc/luna.conf
    Credentials to access to MongoDB.
/var/log/luna/lweb.log
    Log file.
/var/log/luna/lweb_tornado.log
    Log file for HTTP requests from the nodes.
/run/luna/lweb.pid
    PID file.

SEE ALSO
========
ltorrent(1), luna(8), lpower(8), lchroot(8)
