from vcs_support.base import BaseVCS, VCSVersion

import ConfigParser
import subprocess
import os
from socket import gethostname

from projects.exceptions import ProjectImportError

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
        config = ConfigParser.RawConfigParser()

        if not os.path.exists('../authorization.ini'):
            raise ProjectImportError("Authorization configuration file missing")
        config.read('../authorization.ini')

        self.p4_user = config.get('Perforce', 'P4USER')
        if self.p4_user == "NOTSPECIFIED":
            raise ProjectImportError(
                      "Perforce username must be configured in authorization.ini"
                  )

        self.p4_pass = config.get('Perforce', 'P4PASSWD')
        if self.p4_pass == "NOTSPECIFIED":
            raise ProjectImportError(
                      "Perforce password must be configured in authorization.ini"
                  )

    def _login(self):
        ps = subprocess.Popen(
            ['p4', '-u', self.p4_user, 'login'],
            stdin=subprocess.PIPE
        )
        out, err = ps.communicate(self.p4_pass)

    def _clean_repo_url(self):
        if self.repo_url[-1] != '/':
            self.base_url = self.repo_url
            self.repo_url += '/'
        else:
            self.base_url = self.repo_url

    def _run_on_client(self, *args):
        """
        Run a P4 command on the current workspace
        Returns a tuple of (return_code, stdout, stderr)
        """
        workspace_name = self._get_workspace_name()
        return self.run(
            'p4', 
            '-c', workspace_name,  
            *args
        )

    def _workspace_exists(self):
        retcode = self._run_on_client('where', '//...')[0]
        if retcode == 0:
            return True
        return False

    def _get_workspace_name(self):
        return 'read_the_docs_%s' % self.name.replace(' ','-')

    def _create_workspace(self):
        workspace_name = self._get_workspace_name()
        filled_template = WORKSPACE_TEMPLATE.format(
                                                 client_name=workspace_name, 
                                                 owner='hrafng', 
                                                 depot_path=self.repo_url,
                                                 root=self.working_dir,
                                                 hostname=gethostname()
                                             )

        ps = subprocess.Popen(
                            ['p4', 'client', '-i'], 
                            stdin=subprocess.PIPE, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE
                        )

        out, err = ps.communicate(filled_template)
        log.info(out)
        if err:
            raise ProjectImportError(err)

    def _sync(self):
        retcode = self._run_on_client('sync')[0]
        if retcode != 0:
            raise ProjectImportError(
                      "Failed to sync client '{workspace}'".format(
                          workspace=self._get_workspace_name()
                      )
                  )

        # Force sync conf files because they get modified by the doc builder
        retcode = self._run_on_client(
                           'sync', '-f', '//...conf.py'
                       )[0]

        if retcode != 0:
            raise ProjectImportError("Failed to force sync .conf files")
   
    def update(self):
        """
        If self.working_dir is already a valid local copy of the repository,
        update the repository, else create a new local copy of the repository.
        """
        super(Backend, self).update()
        self._login()
        if not self._workspace_exists():
            self._create_workspace()
        self._sync()

    def checkout(self, identifier=None):
        super(Backend, self).checkout()
        self._login()
        self._create_workspace()
        self._sync()


