#!/bin/bash

# Written by Dmitry Chirikov <dmitry@chirikov.ru>
# This file is part of Luna, cluster provisioning tool
# https://github.com/dchirikov/luna

# This file is part of Luna.

# Luna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Luna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Luna.  If not, see <http://www.gnu.org/licenses/>.

echo "Welcome to Luna Installer"
. /lib/dracut-lib.sh
function luna_start () {
    local luna_ip
    echo "$(getargs luna.node=)" > /proc/sys/kernel/hostname
    echo "Luna: Starting ssh"
    echo "sshd:x:74:74:Privilege-separated SSH:/var/empty/sshd:/sbin/nologin" >> /etc/passwd
    echo sshd:x:74: >> /etc/group
    mkdir -p /var/empty/sshd
    /usr/sbin/sshd > /dev/null 2>&1
    echo "Luna: Start shell on tty2"
    luna_ctty2=/dev/tty2
    setsid -c /bin/sh -i -l 0<>$luna_ctty2 1<>$luna_ctty2 2<>$luna_ctty2 &
    udevadm settle
    echo "Luna: Set-up network"
    luna_ip=$(getargs luna.ip=)
    if [ "x$luna_ip" = "xdhcp" ]; then 
        echo "Luna: No luna.ip specified. Running dhcp"
        /usr/sbin/dhclient -lf /luna/dhclient.leases
    else
        echo "Luna: ${luna_ip##*:} for interface ${luna_ip%%:*} was specified"
        ip a add ${luna_ip##*:} dev ${luna_ip%%:*}
        sleep 1
        ip l set dev ${luna_ip%%:*} up
    fi
}

function luna_finish () {
    # shutdown sshd
    /usr/bin/ps h --ppid `cat /var/run/sshd.pid` -o 'pid' | while read pid; do kill $pid; done
    kill `cat /var/run/sshd.pid`
    # shutdown dhclient
    /usr/sbin/dhclient -lf /luna/dhclient.leases -x
    # bring interfaces down
    luna_ip=$(getargs luna.ip=)
    if [ "x$luna_ip" = "xdhcp" ]; then
        /usr/bin/cat /luna/dhclient.leases  | \
            /usr/bin/sed -n '/interface /s/\W*interface "\(.*\)";/\1/p' | \
            while read iface; do 
                /usr/sbin/ip addr flush $iface
                /usr/sbin/ip link set dev $iface down
            done
    else
        /usr/sbin/ip addr flush ${luna_ip%%:*}
        /usr/sbin/ip link set dev ${luna_ip%%:*} down
    fi
    # kill shell on tty2
    ps h t tty2 o pid | while read pid; do kill -9 $pid; done

}
function _get_luna_ctty () {
    local luna_ctty
    luna_ctty=$(getargs luna.ctty=)
    # TODO [ "x${luna_ctty}" = "x" ] && luna_ctty=$(getargs console=)
    [ "x${luna_ctty}" = "x" ] && luna_ctty="/dev/tty1"
    echo -n $luna_ctty
}
if [ "x$root" = "xluna" ]; then 
    luna_start
    #luna_ctty=/dev/tty1
    luna_ctty=$(_get_luna_ctty)
    echo luna_ctty=$luna_ctty
    luna_url=$(getargs luna.url=)
    luna_node=$(getargs luna.node=)
    luna_delay=$(getargs luna.delay=)
    [ -z $luna_delay ] || luna_delay=20
    luna_service=$(getargs luna.service=)
    if [ "x$luna_service" = "x1" ]; then
        echo "Luna: Entering Service mode."
        setsid -c /bin/sh -i -l 0<>$luna_ctty 1<>$luna_ctty 2<>$luna_ctty
    else
        RES="failure"
        while [ "x$RES" = "xfailure" ]; do
            echo "Luna: Trying to get install script."
            while ! curl -f -s -m 60 --connect-timeout 10 "$luna_url?step=install&node=$luna_node" > /luna/install.sh; do 
                echo "Luna: Could not get install script. Sleeping $luna_delay sec."
                sleep $luna_delay
            done
            /bin/sh /luna/install.sh && RES="success"
            echo "Luna: install.sh exit status: $RES" 
            sleep 10
        done
    fi
    luna_finish
    echo 'Exit from Luna Installer'
fi
