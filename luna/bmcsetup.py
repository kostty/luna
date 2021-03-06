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

from luna.base import Base
from luna.cluster import Cluster


class BMCSetup(Base):
    """
    Class for operating with BMCSetup records.
    These are used by luna for auth and communicate with BMC devices found
    on the managed nodes
    """

    log = logging.getLogger(__name__)

    def __init__(self, name=None, mongo_db=None, create=False, id=None,
                 userid=3, user='ladmin', password='ladmin',
                 netchannel=1, mgmtchannel=1):
        """
        userid      - default user id
        user        - username
        password    - pasword
        netchannel  - network channel
        mgmtchannel - management channel
        """

        self.log.debug("function args '{}".format(self._debug_function()))

        # Define the schema used to represent BMC configuration objects

        self._collection_name = 'bmcsetup'
        self._keylist = {'userid': type(0),
                         'user': type(''), 'password': type(''),
                         'netchannel': type(0), 'mgmtchannel': type(0)}

        # Check if this BMC config is already present in the datastore
        # Read it if that is the case

        bmc = self._check_name(name, mongo_db, create, id)

        if create:
            cluster = Cluster(mongo_db=self._mongo_db)

            # Verify that all the keywords arguments have the correct types
            # as specified in the self._keylist

            args = locals()

            for key in self._keylist:
                if type(args[key]) is not self._keylist[key]:
                    self.log.error(("Argument '{}' should be '{}'"
                                    .format(key, self._keylist[key])))
                    raise RuntimeError

            # Define a new mongo document

            bmc = {'name': name, 'userid': userid, 'user': user,
                   'password': password, 'netchannel': netchannel,
                   'mgmtchannel': mgmtchannel}

            # Store the new BMC config in the datastore

            self.log.debug("Saving BMC conf '{}' to the datastore".format(bmc))

            self._name = name
            self._id = self._mongo_collection.insert(bmc)
            self._DBRef = DBRef(self._collection_name, self._id)

            # Link this BMC config to the current cluster

            self.link(cluster)

        else:
            self._name = bmc['name']
            self._id = bmc['_id']
            self._DBRef = DBRef(self._collection_name, self._id)

        self.log = logging.getLogger(__name__ + '.' + self._name)
