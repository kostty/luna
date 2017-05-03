'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

import re
import socket
import struct
import logging


log = logging.getLogger(__name__)


def ntoa(num_ip):
    """
    Convert the IP numip from the binary notation
    into the IPv4 numbers-and-dots form
    """

    try:
        # '>L' stands for a bigendian unsigned long

        ip = socket.inet_ntoa(struct.pack('>L', num_ip))
        return ip

    except:
        log.error(("Cannot convert '{}' from C"
                   " to IPv4 format".format(num_ip)))
        raise RuntimeError


def aton(ip):
    """
    Convert the IP ip from the IPv4 numbers-and-dots
    notation into binary form (in network byte order)
    """

    try:
        absnum = struct.unpack('>L', (socket.inet_aton(ip)))[0]
        return long(absnum)

    except:
        log.error("Cannot convert IP '{}' to C format".format(ip))
        raise RuntimeError


def reltoa(num_net, rel_ip):
    """
    Convert a relative ip (a number relative to the base of the
    network obtained using 'get_num_subnet') into an IPv4 address
    """

    num_ip = int(num_net) + int(rel_ip)
    return ntoa(num_ip)


def atorel(ip, num_net, prefix):
    """
    Convert an IPv4 address into a number relative to the base of
    the network obtained using 'get_num_subnet'
    """

    num_ip = aton(ip)

    # Check if the ip address actually belongs to num_net/prefix
    if not ip_in_net(ip, num_net, prefix):
        log.error(("Network '{}/{}' does not contain '{}'"
                   .format(ntoa(num_net), prefix, ip)))
        raise RuntimeError

    relative_num = long(num_ip - num_net)

    return relative_num


def get_num_subnet(ip, prefix):
    """
    Get the address of the subnet to which ip belongs in binary form
    """
    try:
        prefix = int(prefix)
    except:
        log.error("Prefix '{}' is invalid, must be 'int'".format(prefix))
        raise RuntimeError

    if prefix not in range(1, 32):
        log.error("Prefix should be in the range [1..32]")
        raise RuntimeError

    if type(ip) is long or type(ip) is int:
        num_ip = ip
    else:
        try:
            num_ip = aton(ip)
        except socket.error:
            log.error("'{}' is not a valid IP".format(ip))
            raise RuntimeError

    num_mask = ((1 << 32) - 1) ^ ((1 << (33 - prefix) - 1) - 1)
    num_subnet = long(num_ip & num_mask)

    return num_subnet


def ip_in_net(ip, num_net, prefix):
    """
    Check if an address (either in binary or IPv4 form) belongs to
    num_net/prefix
    """

    if type(ip) is long or type(ip) is int:
        num_ip = ip
    else:
        num_ip = aton(ip)

    num_subnet1 = get_num_subnet(num_net, prefix)
    num_subnet2 = get_num_subnet(ip, prefix)

    return num_subnet1 == num_subnet2


def guess_ns_hostname():
    """
    Try to guess the hostname to use for the nameserver
    it supports hosts of the format host-N, hostN for HA
    configurations. Returns the current hostname otherwise
    """
    ns_hostname = socket.gethostname().split('.')[0]

    if ns_hostname[-1:].isdigit():
        guessed_name = re.match('(.*)[0-9]+$', ns_hostname).group(1)

        if guessed_name[-1] == '-':
            guessed_name = guessed_name[:-1]

        try:
            guessed_ip = socket.gethostbyname(guessed_name)
        except:
            guessed_ip = None

        if guessed_ip:
            log.info(("Guessed that NS server should be '%s', "
                      "instead of '%s'. "
                      "Please update if this is not correct.") %
                     (guessed_name, ns_hostname))
            return guessed_name

    # Return the current host's hostname if the guessed name could not
    # be resolved
    return ns_hostname
