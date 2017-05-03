from ming import create_datastore
import mock
import unittest

import os
import luna
import getpass


class NetworkCreateTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())

    def tearDown(self):
        self.bind.conn.drop_all()

    def test_create_network_with_defaults(self):
        net = luna.Network(name='testnet', mongo_db=self.db, create=True,
                           NETWORK='172.16.1.0', PREFIX='24')
        self.assertIsInstance(net, luna.Network)


class NetworkReadTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        cluster = luna.Cluster(mongo_db=self.db, create=True,
                               path=self.path, user=getpass.getuser())

    def tearDown(self):
        self.bind.conn.drop_all()

    def test_read_non_existing_network(self):
        self.assertRaises(RuntimeError, luna.Network, mongo_db=self.db)

    def test_read_network(self):
        luna.Network(name='testnet', mongo_db=self.db, create=True,
                     NETWORK='172.16.1.0', PREFIX='24')
        net = luna.Network(name='testnet', mongo_db=self.db)
        self.assertIsInstance(net, luna.Network)


class NetworkAttributesTests(unittest.TestCase):

    def setUp(self):
        self.bind = create_datastore('mim:///luna')
        self.db = self.bind.db.luna
        self.path = '/tmp/luna'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        cluster = luna.Cluster(mongo_db=self.db, create=True, path=self.path,
                               user=getpass.getuser())
        self.net = luna.Network(name='test', mongo_db=self.db, create=True,
                                NETWORK='172.16.1.0', PREFIX='24',
                                ns_hostname='controller', ns_ip='172.16.1.254')

    def tearDown(self):
        self.bind.conn.drop_all()

    def test_get_network(self):
        self.assertEqual(self.net.get('NETWORK'), '172.16.1.0')

    def test_get_netmask(self):
        self.assertEqual(self.net.get('NETMASK'), '255.255.255.0')

    def test_get_PREFIX(self):
        self.assertEqual(self.net.get('PREFIX'), '24')

    def test_get_ns_ip(self):
        self.assertEqual(self.net.get('ns_ip'), '172.16.1.254')

    def test_get_other_key(self):
        self.assertEqual(self.net.get('name'), 'test')

    def test_reserve_ip(self):
        self.net.reserve_ip('172.16.1.3')
        net = self.net._get_json()
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 2},
                                           {'start': 4, 'end': 253}])

    def test_reserve_ip_range(self):
        self.net.reserve_ip('172.16.1.4', '172.16.1.6')
        net = self.net._get_json()
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 3},
                                           {'start': 7, 'end': 253}])

    def test_release_ip(self):
        self.net.release_ip('172.16.1.254')
        net = self.net._get_json()
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 254}])

    def test_release_ip_range(self):
        self.net.release_ip('172.16.1.250', '172.16.1.254')
        net = self.net._get_json()
        self.assertEqual(net['freelist'], [{'start': 1, 'end': 254}])

    def test__save_free_list(self):
        self.net._save_free_list([{'start': 10, 'end': 50}])
        net = self.net._get_json()
        self.assertEqual(net['freelist'], [{'start': 10, 'end': 50}])


if __name__ == '__main__':
    unittest.main()
