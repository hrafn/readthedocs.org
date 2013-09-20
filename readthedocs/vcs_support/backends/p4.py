
from vcs_support.base import BaseVCS, VCSVersion

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
Options:        nomodtime clobber
SubmitOptions:  submitunchanged
View:
        {depot_path}...     "//{client_name}/..."
"""

class Backend(BaseVCS):
    supports_tags = False
    fallback_branch = ''

    def __init__(self, project, version):
        super(Backend, self).__init__(project, version)
        self._clean_repo_url()
        self._load_configuration()

    def _load_configuration(self):
        self.p4_user = getattr(settings, 'P4USER')
        if self.p4_user == "NOTSPECIFIED":
            raise ProjectImportError(
                      "Perforce username must be configured"
                  )

        self.p4_pass = getattr(settings, 'P4PASSWD')
        if self.p4_pass == "NOTSPECIFIED":
            raise ProjectImportError(
                      "Perforce user credentials must be configured"
                  )

    def _login(self):
        ps = subprocess.Popen(
            ['p4', '-u', self.p4_user, 'login', '-p'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = ps.communicate(self.p4_pass)
        self.p4_ticket = out.replace('\n', '').replace('\r', '').split(' ')[-1]
        log.info('Ticket: "%s"', self.p4_ticket)

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
            '-u', self.p4_user,
            '-P', self.p4_ticket,
            '-c', workspace_name,  
            *args
        )

    def _workspace_exists(self):
        retcode = self._run_on_client('where', '//...')[0]
        if retcode == 0:
            return True
        return False

    def _get_workspace_name(self):
        return 'read_the_docs_{project_name}_{host_name}'.format(
            project_name=self.name.replace(' ','-'),
            host_name=gethostname()
        )

    def _create_workspace(self):
        workspace_name = self._get_workspace_name()
        filled_template = WORKSPACE_TEMPLATE.format(
                                                 client_name=workspace_name, 
                                                 owner=self.p4_user, 
                                                 depot_path=self.repo_url,
                                                 root=self.working_dir,
                                                 hostname=gethostname(),
                                                 project_name=self.name
                                             )

        ps = subprocess.Popen(
                            ['p4', '-u', self.p4_user, '-P', self.p4_ticket, 'client', '-i'], 
                            stdin=subprocess.PIPE, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE
                        )
        log.debug(['p4', '-u', self.p4_user, '-P', self.p4_ticket, 'client', '-i'])

        out, err = ps.communicate(filled_template)
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


