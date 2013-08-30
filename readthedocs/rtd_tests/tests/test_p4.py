import os

from rtd_tests.tests.base import RTDTestCase

from vcs_support.backends import p4
from vcs_support.base import VCSProject

class TestP4(RTDTestCase):
    def setUp(self):
        project = VCSProject(
                      "testname", 
                      'testDefaultBranch', 
                      '/home/vagrant/TestCheckout', 
                      '//depot/games/branches/development/MAIN/eve/common/modules/sake')
        self.p4 = p4.Backend(project, "1.0")
        self.build_dir = '/home/vagrant/TestBuild'
        self.p4.run('mkdir', self.build_dir) # So teardown won't fail


    def test_workspace_exists(self):
        nonexistant_workspace_exists = self.p4._workspace_exists('hrafng_test01')
        self.assertFalse(nonexistant_workspace_exists)
        existing_workspace_exists = self.p4._workspace_exists('lucid32')
        self.assertTrue(existing_workspace_exists)


    def test_create_workspace(self):
        self.p4._create_workspace()
        assert os.path.exists(self.build_dir)

    def test_checkout(self):
        self.p4.checkout(None)
        
