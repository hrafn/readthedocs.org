from vcs_support.base import BaseVCS, VCSVersion
import ConfigParser
import subprocess
import os
from socket import gethostname
from projects.exceptions import ProjectImportError
from django.conf import settings
import logging
log = logging.getLogger(__name__)

WORKSPACE_TEMPLATE = """
Client: {client_name}
Owner:  {owner}
Description:
        A workspace for Read The Docs
Root:   {root}
Host: {hostname}
Options:        nomodtime noclobber
SubmitOptions:  submitunchanged
View:
        {depot_path}...     "//{client_name}/..."
"""

class Backend(BaseVCS):
    supports_tags=False
    fallback_branch=''

    def __init__(self, project, version):
        super(Backend, self).__init__(project, version)
        self._clean_repo_url()
        self._load_configuration()

    def _load_configuration(self):
        """
        Read P4USER and P4PASSWD from authorization.ini
        """
        config = ConfigParser.RawConfigParser()
        ini_file_path = os.path.join(settings.SITE_ROOT, 'authorization.ini')

        if not os.path.exists(ini_file_path):
            raise ProjectImportError("Authorization configuration file missing")
        config.read(ini_file_path)

        self.p4_user = config.get('Perforce', 'P4USER')
        if self.p4_user == "NOTSPECIFIED":
            raise ProjectImportError(
                      "Perforce username must be configured in authorization.ini"
                  )

        self.p4_pass = config.get('Perforce', 'P4PASSWD')
        if self.p4_pass == "NOTSPECIFIED":
            raise ProjectImportError(
                      "Perforce user credentials must be configured in %s" % ini_file_path
                  )

    def _clean_repo_url(self):
        """
        Make sure the repo url ends with a trailing slash
        """
        if self.repo_url[-1] != '/':
            self.repo_url += '/'

    def _run_p4_command(self, *args):
        """
        Run a p4 command with authorization.
        """
        os.environ["P4USER"] = self.p4_user
        os.environ["P4PASSWD"] = self.p4_pass

        ps = subprocess.Popen(
                          args, 
                          shell=False,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
        
        stdout, stderr = ps.communicate()
        return ps.returncode

    def _run_on_client(self, *args):
        """
        Run a P4 command on the current workspace
        Returns the return code of the process
        """
        workspace_name = self._get_workspace_name()
        return self._run_p4_command(
            'p4',
            '-u', self.p4_user,
            '-c', workspace_name, 
            *args)

    def _workspace_exists(self):
        """
        Check if a workspace already exists.
        """
        retcode = self._run_on_client('where', '//...')
        if retcode == 0:
            return True
        return False

    def _get_workspace_name(self):
        """
        Create the Perforce workspace name for the current project.
        """
        return 'read_the_docs_%s' % self.name.replace(' ','-')

    def _create_workspace(self):
        workspace_name = self._get_workspace_name()
        filled_template = WORKSPACE_TEMPLATE.format(
                                                 client_name=workspace_name, 
                                                 owner=self.p4_user, 
                                                 depot_path=self.repo_url,
                                                 root=self.working_dir,
                                                 hostname=gethostname()
                                             )
        os.environ["P4USER"] = self.p4_user
        os.environ["P4PASSWD"] = self.p4_pass

        ps = subprocess.Popen(
                            ['p4', 'client', '-i'], 
                            stdin=subprocess.PIPE, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                        )

        out, err = ps.communicate(filled_template)
        if err:
            raise ProjectImportError(err)

    def _sync(self):
        """
        Sync the workspace for the current project.
        """
        retcode = self._run_on_client('sync')
        if retcode != 0:
            raise ProjectImportError(
                      "Failed to sync client '{workspace}'".format(
                          workspace=self._get_workspace_name()
                      )
                  )
        # Force sync conf files because they get modified by the doc builder
        retcode = self._run_on_client(
                           'sync', '-f', '//...conf.py'
                       )

        if retcode != 0:
            raise ProjectImportError("Failed to force sync .conf files")
   
    def update(self):
        """
        If self.working_dir is already a valid local copy of the repository,
        update the repository, else create a new local copy of the repository.
        """
        super(Backend, self).update()
        if not self._workspace_exists():
            self._create_workspace()
        self._sync()

    def checkout(self, identifier=None):
        """
        Create a workspace and sync it.
        """
        super(Backend, self).checkout()
        self._create_workspace()
        self._sync()


