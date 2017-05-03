======
lpower
======

---------------------------------------
command to remotely power control nodes
---------------------------------------

:Author: Dmitry Chirikov
:Date:   October 2016
:Manual section: 8

SYNOPSIS
========

**lpower** [ *--help* | *-h* ] *hostlist* [ *status* | *on* | *off* | *reset* | *cycle* | *identify* | *noidentify* ]

DESCRIPTION
===========

**lpower** is used to remote control power state of nodes

OPTIONS
=======

**--help**, **-h**
    Get a quick overview of the options.

*hostlist*
    Range of the nodes: node[001-005,007-009,011], etc.

**status**
    Get power status of the nodes.

**on**
    Power on node.

**off**
    Power off node.

**reset**
    Reset node. The equivalent to the old Ctrl-Alt-Del.

**cycle**
    Do a power cycle of the node. Switch it off, then turn it on back.

**identify**
    Light identity LED on for 255 seconds.

**noidentify**
    Switch  identity LED off.

FILES
=====

/etc/luna.conf
    Credentials to access to MongoDB.


SEE ALSO
========
lweb(1), ltorrent(1), luna(8), lchroot(8)
