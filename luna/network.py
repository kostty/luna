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

from config import *

import logging

from bson.dbref import DBRef
from bson.objectid import ObjectId

from luna import utils
from luna.base import Base
from luna.cluster import Cluster


class Network(Base):
    """Class for operating with network objects"""

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False, id=None,
                 NETWORK=None, PREFIX=None, ns_hostname=None, ns_ip=None):
        """
        create  - should be True if we need create a network
        NETWORK - network
        PREFIX  - the prefix in a networks CIDR format
        """

        self.log.debug("function {} args".format(self._debug_function()))

        # Define the schema used to represent network objects

        self._collection_name = 'network'
        self._keylist = {'NETWORK': long, 'PREFIX': type(''),
                         'ns_hostname': type(''), 'ns_ip': type('')}

        # Check if this network is already present in the datastore
        # Read it if that is the case

        net = self._check_name(name, mongo_db, create, id)

        if create:
            cluster = Cluster(mongo_db=self._mongo_db)
            num_subnet = utils.ip.get_num_subnet(NETWORK, PREFIX)
            flist = [{'start': 1, 'end': (1 << (32 - int(PREFIX))) - 2}]

            # Try to guess the nameserver hostname if none provided

            if not ns_hostname:
                ns_hostname = utils.ip.guess_ns_hostname()

            # Define a new mongo document

            net = {'name': name, 'NETWORK': num_subnet, 'PREFIX': PREFIX,
                   'freelist': flist, 'ns_hostname': ns_hostname,
                   'ns_ip': None}

            # Store the new network in the datastore

            self.log.debug("Saving net '{}' to the datastore".format(net))

            self._name = name
            self._id = self._mongo_collection.insert(net)
            self._DBRef = DBRef(self._collection_name, self._id)

            # Link this network to the current cluster

            self.link(cluster)

            # If no IP address is provided for the nameserver, default to
            # the cluster's frontend address

            if ns_ip is None:
                ns_ip = utils.ip.reltoa(num_subnet, flist[0]['end'])

            self.set('ns_ip', ns_ip)

        else:
            self._name = net['name']
            self._id = net['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

        self.log = logging.getLogger(__name__ + '.' + self._name)

    def set(self, key, value):
        if not bool(key) or type(key) is not str:
            self.log.error("Field should be specified")
            return None

        if key not in self._keylist:
            self.log.error("Cannot change '{}' field".format(key))
            return None

        net = self._get_json()

        if key == 'ns_ip':
            rel_ns_ip = utils.ip.atorel(value, net['NETWORK'], net['PREFIX'])
            old_ip = None

            try:
                old_ip = self.get('ns_ip')
            except:
                pass

            if bool(old_ip):
                self.release_ip(old_ip)

            self.reserve_ip(rel_ns_ip)
            net = self._get_json()
            net['ns_ip'] = rel_ns_ip

        elif key == 'ns_hostname':
            net['ns_hostname'] = value

        elif key == 'NETWORK':
            prefix = net['PREFIX']
            num_subnet = utils.ip.get_num_subnet(value, prefix)

            net['NETWORK'] = num_subnet

        elif key == 'PREFIX':
            num_subnet = net['NETWORK']
            new_num_subnet = utils.ip.get_num_subnet(num_subnet, value)

            limit = (1 << (32 - value)) - 1
            net['freelist'] = utils.freelist.set_upper_limit(net['freelist'],
                                                             limit)
            net['NETWORK'] = new_num_subnet
            net['PREFIX'] = value

        ret = self._mongo_collection.update({'_id': self._id},
                                            {'$set': net},
                                            multi=False, upsert=False)
        return not ret['err']

    def get(self, key):
        if not key or type(key) is not str:
            return None

        net = self._get_json()

        if key == 'NETWORK':
            return utils.ip.ntoa(net[key])

        if key == 'NETMASK':
            prefix = int(net['PREFIX'])
            num_mask = ((1 << 32) - 1) ^ ((1 << (33 - prefix) - 1) - 1)

            return utils.ip.ntoa(num_mask)

        if key == 'PREFIX':
            return net['PREFIX']

        if key == 'ns_ip':
            return utils.ip.reltoa(net['NETWORK'], net['ns_ip'])

        return super(Network, self).get(key)

    def _save_free_list(self, flist):
        self.log.debug("function args '{}'".format(self._debug_function()))

        if not self._id:
            self.log.error("Couldn't update network. Was it deleted?")
            return None

        res = self._mongo_collection.update({'_id': self._id},
                                            {'$set': {'freelist': flist}},
                                            multi=False, upsert=False)

        if res['err']:
            self.log.error("Error updating freelist '{}'".format(flist))

        return not res['err']

    def reserve_ip(self, ip1=None, ip2=None, ignore_errors=True):
        net = self._get_json()

        if type(ip1) is str:
            ip1 = utils.ip.atorel(ip1, net['NETWORK'], net['PREFIX'])

        if type(ip2) is str:
            ip2 = utils.ip.atorel(ip2, net['NETWORK'], net['PREFIX'])

        if bool(ip2) and ip2 <= ip1:
            self.log.error("Wrong range definition.")
            return None

        if bool(ip1):
            flist, unfreed = utils.freelist.unfree_range(net['freelist'],
                                                         ip1, ip2)

        elif ignore_errors:
            flist, unfreed = utils.freelist.next_free(net['freelist'])

        self._save_free_list(flist)

        return unfreed

    def release_ip(self, ip1, ip2=None):
        net = self._get_json()

        if type(ip1) is str:
            ip1 = utils.ip.atorel(ip1, net['NETWORK'], net['PREFIX'])

        if type(ip2) is str:
            ip2 = utils.ip.atorel(ip2, net['NETWORK'], net['PREFIX'])

        if bool(ip2) and ip2 <= ip1:
            self.log.error("Wrong range definition.")
            return None

        flist, freed = utils.freelist.free_range(net['freelist'], ip1, ip2)
        self._save_free_list(flist)

        return True

    def resolve_used_ips(self):
        from luna.switch import Switch
        from luna.otherdev import OtherDev
        from luna.node import Group

        net = self._get_json()

        try:
            rev_links = net[usedby_key]
        except:
            self.log.error(("No IPs configured for network '{}'"
                            .format(self.name)))
            return {}

        out_dict = {}

        def add_to_out_dict(name, relative_ip):
            try:
                out_dict[name]
                self.log.error(("Duplicate name '{}' in network '{}'"
                                .format(name, self.name)))
            except:
                out_dict[name] = utils.ip.reltoa(net['NETWORK'], relative_ip)

        for elem in rev_links:
            if elem == "group":
                for gid in rev_links[elem]:
                    group = Group(id=ObjectId(gid), mongo_db=self._mongo_db)
                    tmp_dict = group.get_rel_ips_for_net(self.id)

                    for nodename in tmp_dict:
                        add_to_out_dict(nodename, tmp_dict[nodename])

            if elem == "switch":
                for sid in rev_links[elem]:
                    switch = Switch(id=ObjectId(sid), mongo_db=self._mongo_db)
                    add_to_out_dict(switch.name, switch.get_rel_ip())

            if elem == "otherdev":
                for oid in rev_links[elem]:
                    odev = OtherDev(id=ObjectId(oid), mongo_db=self._mongo_db)
                    add_to_out_dict(odev.name, odev.get_ip(self.id))

        add_to_out_dict(net['ns_hostname'], net['ns_ip'])

        return out_dict
