#/usr/bin/env python
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


import luna
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen
import threading
import datetime
import time
from bson.dbref import DBRef
from luna import utils

last_switch_update = None
lock_last_switch_update = threading.Lock()
switch_table_updater_running = False
lock_switch_table_updater_running = threading.Lock()
switch_mac_table = None
lock_switch_mac_table = threading.Lock()


class Manager(tornado.web.RequestHandler):

    def initialize(self, params):
        self.server_ip = params['server_ip']
        self.server_port = params['server_port']
        self.mongo = params['mongo_db']
        self.app_logger = params['app_logger']

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        step = self.get_argument('step')

        if step == 'boot':
            nodes = luna.list('node')
            self.render("templ_ipxe.cfg", server_ip = self.server_ip, server_port = self.server_port, nodes = nodes)

        if step == 'discovery':
            try:
                hwdata = self.get_argument('hwdata')
            except:
                hwdata = None
            if not bool(hwdata):
                self.send_error(400) #  Bad Request
                return
            try:
                req_nodename = self.get_argument('node')
            except:
                req_nodename = None
            try:
                boot_type = self.get_argument('type')
            except:
                boot_type = 'ipxe'
            macs = set(hwdata.split('|'))
            # enter node name manualy from ipxe
            if req_nodename:
                self.app_logger.info("Node '{}' was chosen in iPXE".format(req_nodename))
                try:
                    node = luna.Node(name = req_nodename, mongo_db = self.mongo)
                except:
                    self.app_logger.error("No such node configured in DB. '{}'".format(req_nodename))
                    self.send_error(400)
                    return
                mac = None
                for mac in macs:
                    if bool(mac):
                        mac = str(mac.lower())
                        self.app_logger.info("Node '{}' trying to set '{}' as mac".format(req_nodename, mac))
                        if node.set_mac(mac):
                            node.update_status('boot.mac_assigned')
                            break
                        self.app_logger.error("MAC: '{}' looks wrong.".format(mac))
            # need to find node fo given macs.
            # first step - trying to find in know macs
            found_node_dbref = None
            for mac in macs:
                if not bool(mac):
                    continue
                mac = mac.lower()
                try:
                    found_node_dbref = self.mongo['mac'].find_one({'mac': mac}, {'_id': 0, 'node': 1})['node']
                except:
                    #self.app_logger.error("Mac record exists, but no node configured for given mac '{}'".format(mac))
                    #self.send_error(404)
                    #return
                    continue
                if bool(found_node_dbref):
                    break

            # second step. now try to find in learned switch macs if we have switch/port configured
            if not bool(found_node_dbref):
                mac_from_cache = None
                for mac in macs:
                    #mac_cursor = self.mongo['switch_mac'].find({'mac': mac}).sort([('updated', -1)]).limit(1)
                    mac_cursor = self.mongo['switch_mac'].find({'mac': mac})
                    # first search mac in switch_mac using portnames like 'Gi2/0/26'
                    for elem in mac_cursor:
                        switch_id = elem['switch_id']
                        portname = elem['portname']
                        try:
                            node_id = self.mongo['node'].find_one({'switch': DBRef('switch', switch_id), 'port': portname}, {})['_id']
                            mac_from_cache = mac
                        except:
                            node_id = None
                            mac_from_cache = None
                        if mac_from_cache:
                            break
                    if mac_from_cache:
                        break
                    mac_cursor = self.mongo['switch_mac'].find({'mac': mac})
                    # now search mac in switch_mac using portnumbers
                    for elem in mac_cursor:
                        switch_id = elem['switch_id']
                        port = elem['port']
                        try:
                            node_id = self.mongo['node'].find_one({'switch': DBRef('switch', switch_id), 'port': port}, {})['_id']
                            mac_from_cache = mac
                        except:
                            node_id = None
                            mac_from_cache = None
                        if mac_from_cache:
                            break
                    if mac_from_cache:
                        break
                if not bool(mac_from_cache):
                    self.app_logger.info("Cannot find '{}' in learned macs.".format("', '".join([mac for mac in macs])))
                    # did not find in learned macs
                    self.send_error(404)
                    return
                # here we should have node_id and mac_from_cache
                try:
                    node = luna.Node(id = node_id, mongo_db = self.mongo)
                    utils.helpers.set_mac_node(mac_from_cache, node.DBRef)
                    found_node_dbref = node.DBRef
                except:
                    # should not be here
                    self.app_logger.info("Cannot create node object for '{}' and '{}'".format(found_name_from_learned, self.mongo))
                    self.send_error(404)
                    return
            # here we should have found_node_dbref
            try:
                node = luna.Node(id = found_node_dbref.id, mongo_db = self.mongo)
            except:
                # should not be here
                self.app_logger.info("Cannot create node object for '{}' and '{}'".format(found_node_dbref, self.mongo))
                self.send_error(404)
                return
            # found node finally
            #http_path = "http://" + self.server_ip + ":" + str(self.server_port) + "/boot/"
            boot_params = node.boot_params
            if not boot_params['boot_if']:
                boot_params['ifcfg'] = 'dhcp'
            else:
                boot_params['ifcfg'] = boot_params['boot_if'] + ":" + boot_params['ip'] + "/" + str(boot_params['net_prefix'])
            boot_params['delay'] = 10
            boot_params['server_ip'] = self.server_ip
            boot_params['server_port'] = self.server_port
            if boot_type == 'ipxe':
                node.update_status('boot.request')
                self.render("templ_nodeboot.cfg", p = boot_params)
            elif boot_type == 'syslinux':
                node.update_status('boot.request')
                self.render("templ_nodeboot_syslinux.cfg", p = boot_params)
            else:
                self.send_error(404)

        if step == 'install':
            try:
                node_name = self.get_argument('node')
            except:
                self.app_logger.error("No nodename for install step specified.")
                #return self.send_error(400)
                self.send_error(400)
                return
            try:
                node = luna.Node(name = node_name, mongo_db = self.mongo)
            except:
                self.app_logger.error("No such node for install step found '{}'.".format(node_name))
                #return self.send_error(400)
                self.send_error(400)
                return
                #self.finish()
            try:
                status = self.get_argument('status')
            except:
                status = ''
            if bool(status):
                node.update_status(status)
                self.finish()
                return
            install_params = node.install_params
            if not bool(install_params['torrent']):
                #return self.send_error(404)
                self.send_error(404)
                return
                #self.finish()
            node.update_status('install.request')
            self.render("templ_install.cfg", p = install_params, server_ip = self.server_ip, server_port = self.server_port,)

