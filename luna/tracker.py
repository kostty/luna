#!/usr/bin/env python
#
# Based on Pytt by
# @author: Sreejith K <sreejithemk@gmail.com>
# Created on 12th May 2011
# http://foobarnbaz.com
#
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

import logging
import sys
import pymongo
import binascii
import datetime
import random
from socket import inet_aton
from struct import pack
from httplib import responses


import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen

from libtorrent import bencode
import luna

#db_name = 'luna'

#logger = logging.getLogger('tornado.access')

class BaseHandler(tornado.web.RequestHandler):
    """
    info_hach and peer_id can contain non-unicode symbols
    """
    def decode_argument(self, value, name):
        # info_hash is raw_bytes, hexify it.
        if name in ['info_hash', 'peer_id'] :
            value = binascii.hexlify(value)
        return super(BaseHandler, self).decode_argument(value, name)


class AnnounceHandler(BaseHandler):
    """Track the torrents. Respond with the peer-list.
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def update_peers(self, info_hash, peer_id, ip, port, status, uploaded, downloaded, left):
        """Store the information about the peer.
        """
        updated = datetime.datetime.utcnow()
        # json = {'info_hash': info_hash, 'peer_id': peer_id,
        json = {'peer_id': peer_id, 'status': status, 'updated': updated,
                'uploaded': uploaded, 'downloaded': downloaded, 'left': left}
        if not bool(status):
            json.pop('status')
        self.mongo_db['tracker'].find_and_modify({'info_hash': info_hash, 'ip': ip, 'port': port}, {'$set': json}, upsert = True)

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get_peers(self, info_hash, numwant, compact, no_peer_id, age):
        time_age = datetime.datetime.utcnow() - datetime.timedelta(seconds = age)
        # '6c756e616c756e616c756e616c756e616c756e61'
        #node_records, server_records = yield [node_future, server_future]
        peer_tuple_list = []
        n_leechers = 0
        n_seeders = 0
        node_cursor = self.mongo_db['tracker'].find({'info_hash': info_hash, 'updated': {'$gte': time_age}}, {'peer_id': 1, 'ip': 1, 'port': 1, 'status': 1})
        #while (yield node_cursor.fetch_next):
        #    doc = node_cursor.next_object()
        for doc in node_cursor:
            try:
                n_leechers += int(doc['status'] == 'started')
                n_seeders += int(doc['status'] == 'completed')
            except:
                pass
            peer_tuple_list.extend([(binascii.unhexlify(doc['peer_id']), doc['ip'], doc['port'])])
        server_cursor = self.mongo_db['tracker'].find({'info_hash': info_hash, 'peer_id': binascii.hexlify('lunalunalunalunaluna'), 'port': {'$ne': 0}}, {'peer_id': 1, 'ip': 1, 'port': 1, 'status': 1})
        #while (yield server_cursor.fetch_next):
        #    doc = server_cursor.next_object()
        for doc in server_cursor:
            try:
                n_leechers += int(doc['status'] == 'started')
                n_seeders += int(doc['status'] == 'completed')
            except:
                pass
            peer_tuple_list.extend([(binascii.unhexlify(doc['peer_id']), doc['ip'], doc['port'])])
        # It's believed it will get better 'cohesion'
        if numwant > len(peer_tuple_list):
            numwant = len(peer_tuple_list)
        random_peer_list = random.sample(peer_tuple_list, numwant)
        compact_peers = b''
        peers = []
        for peer_info in random_peer_list:
            if compact:
                try:
                    ip = inet_aton(peer_info[1])
                    port = pack('>H', int(peer_info[2]))
                    compact_peers += (ip+port)
                except:
                    pass
                continue
            p = {}
            p['peer_id'], p['ip'], p['port'] = peer_info
            peers.append(p)
        self.response['complete'] = n_seeders
        self.response['incomplete'] = n_leechers
        if compact:
            logging.debug('compact peer list: %r' % compact_peers)
            peers = compact_peers
            self.response['peers'] = compact_peers
        else:
            logging.debug('peer list: %r' % peers)
            self.response['peers'] = peers
        #return (n_seeders, n_leechers, peers)
        #self.write(bencode(self.response))



    def initialize(self, params):
        self.PEER_INCREASE_LIMIT = 30
        self.DEFAULT_ALLOWED_PEERS = 50
        self.MAX_ALLOWED_PEERS = 200
        self.INFO_HASH_LEN = 20 * 2  # info_hash is hexified.
        self.PEER_ID_LEN = 20  * 2  # peer_hash is hexified.

        # HTTP Error Codes for BitTorrent Tracker
        self.INVALID_REQUEST_TYPE = 100
        self.MISSING_INFO_HASH = 101
        self.MISSING_PEER_ID = 102
        self.MISSING_PORT = 103
        self.INVALID_INFO_HASH = 150
        self.INVALID_PEER_ID = 151
        self.INVALID_NUMWANT = 152
        self.GENERIC_ERROR = 900
        self.PYTT_RESPONSE_MESSAGES = {
            self.INVALID_REQUEST_TYPE: 'Invalid Request type',
            self.MISSING_INFO_HASH: 'Missing info_hash field',
            self.MISSING_PEER_ID: 'Missing peer_id field',
            self.MISSING_PORT: 'Missing port field',
            self.INVALID_INFO_HASH: 'info_hash is not %d bytes' % self.INFO_HASH_LEN,
            self.INVALID_PEER_ID: 'peer_id is not %d bytes' % self.PEER_ID_LEN,
            self.INVALID_NUMWANT: 'Peers more than %d is not allowed.' % self.MAX_ALLOWED_PEERS,
            self.GENERIC_ERROR: 'Error in request',
        }
        responses.update(self.PYTT_RESPONSE_MESSAGES)

        self.luna_tracker_interval = params['luna_tracker_interval']
        self.luna_tracker_min_interval = params['luna_tracker_min_interval']
        self.luna_tracker_maxpeers = params['luna_tracker_maxpeers']
        self.mongo_db = params['mongo_db']

    @tornado.web.asynchronous
    ###@tornado.gen.engine
    def get(self):
        failure_reason = ''
        warning_message = ''

        # get all the required parameters from the HTTP request.
        info_hash = self.get_argument('info_hash')
        try:
            info_hash = self.get_argument('info_hash')
        except:
            self.send_error(self.MISSING_INFO_HASH)
            return
        if len(info_hash) != self.INFO_HASH_LEN:
            self.send_error(self.INVALID_INFO_HASH)
            return
        try:
            peer_id = self.get_argument('peer_id')
        except:
            self.send_error(self.MISSING_PEER_ID)
            return
        if len(peer_id) != self.PEER_ID_LEN:
            self.send_error(self.INVALID_PEER_ID)
            return

        try:
            xreal_ip = self.request.headers.get('X-Real-IP')
        except:
            xreal_ip = None

        try:
            announce_ip = self.get_argument('ip')
        except:
            announce_ip = None

        if announce_ip == '0.0.0.0':
            announce_ip = None

        # can return IP address of the wrong interface. Be careful!
        request_remote_ip = self.request.remote_ip

        ip = announce_ip or xreal_ip or request_remote_ip

        try:
            port = int(self.get_argument('port'))
        except:
            self.send_error(self.MISSING_PORT)
            return
        try:
            uploaded = int(self.get_argument('uploaded'))
        except:
            uploaded = 0
        try:
            downloaded = int(self.get_argument('downloaded'))
        except:
            downloaded = 0
        try:
            left = int(self.get_argument('left'))
        except:
            left = 0
        info_hash = str(info_hash)

        try:
            compact = int(self.get_argument('compact'))
        except:
            compact = 0
        try:
            event = self.get_argument('event')
        except:
            event = ''
        try:
            no_peer_id = int(self.get_argument('no_peer_id'))
        except:
            no_peer_id = 0
        try:
            numwant = int(self.get_argument('numwant'))
        except:
            numwant = self.DEFAULT_ALLOWED_PEERS
        if numwant > self.luna_tracker_maxpeers:
            # XXX: cannot request more than MAX_ALLOWED_PEERS.
            self.send_error(self.INVALID_NUMWANT)
            return
        try:
            tracker_id = self.get_argument('trackerid')
        except:
            tracker_id = ''
 
        self.update_peers(info_hash, peer_id, ip, port, event, uploaded, downloaded, left)

        # generate response
        self.response = {}
        # Interval in seconds that the client should wait between sending
        #    regular requests to the tracker.
        self.response['interval'] = self.luna_tracker_interval
        # Minimum announce interval. If present clients must not re-announce
        #    more frequently than this.
        self.response['min interval'] = self.luna_tracker_min_interval
        self.response['tracker id'] = tracker_id
        if bool(failure_reason):
            self.response['failure reason'] = failure_reason
        if bool(warning_message):
            self.response['warning message'] = warning_message

        self.set_header('Content-Type', 'text/plain')

        self.get_peers(info_hash,
                            numwant,
                            compact,
                            no_peer_id,
                            self.luna_tracker_interval * 2)
        #self.response['complete'] = res_complete
        #self.response['incomplete'] = res_incomplete
        #self.response['peers'] = res_peers
        self.write(bencode(self.response))
        self.finish()


class ScrapeHandler(AnnounceHandler):
    """Returns the state of all torrents this tracker is managing.
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        info_hashes = self.get_arguments('info_hash')
        response = {}
        for info_hash in info_hashes:
            info_hash = str(info_hash)
            response[info_hash] = {}
            numwant = 100
            compact = True
            no_peer_id = 1

            res_complete, res_incomplete, _ = self.get_peers(info_hash, numwant, compact, no_peer_id, self.luna_tracker_interval * 2)
            response[info_hash]['complete'] = res_complete
            response[info_hash]['downloaded'] = res_complete
            response[info_hash]['incomplete'] = res_incomplete

        self.set_header('content-type', 'text/plain')
        self.write(bencode(response))
        self.finish()
