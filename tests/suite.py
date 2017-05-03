import unittest
import test_cluster as cluster
import test_network as network
import test_bmcsetup as bmcsetup
import test_utils_ip as utils_ip
import test_utils_freelist as utils_freelist

loader = unittest.TestLoader()
suite = unittest.TestSuite()

suite.addTests(loader.loadTestsFromModule(utils_ip))
suite.addTests(loader.loadTestsFromModule(utils_freelist))
suite.addTests(loader.loadTestsFromModule(cluster))
suite.addTests(loader.loadTestsFromModule(network))
suite.addTests(loader.loadTestsFromModule(bmcsetup))

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
