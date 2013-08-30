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


    def test_checkout(self):
        self.p4.checkout(None)
        
