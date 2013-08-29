from vcs_support.base import BaseVCS, VCSVersion
import subprocess

from projects.exceptions import ProjectImportError

import logging
log = logging.getLogger(__name__)

WORKSPACE_TEMPLATE = """
Client: {client_name}
Owner:  {owner}
Description:
        A workspace for Read The Docs
Root:   {root}
Options:        nomodtime noclobber
SubmitOptions:  submitunchanged
View:
        {depot_path}...     "//{client_name}/..."
"""

depot_path = '//depot/games/branches/development/MAIN/eve/common/modules/sake'
client_name = 'hrafng_test_client'

class Backend(BaseVCS):
    supports_tags=False
    fallback_branch=''

    def __init__(self, project, version):
        super(Backend, self).__init__(project, version)
        self._clean_repo_url()

    def _clean_repo_url(self):
        if self.repo_url[-1] != '/':
            self.base_url = self.repo_url
            self.repo_url += '/'
        else:
            self.base_url = self.repo_url

    def _workspace_exists(self, workspace_name):
        retcode = self.run('p4', '-c', workspace_name, 'where', '//...')[0]
        if retcode == 0:
            return True
        return False

    def _get_workspace_name(self):
        return 'read_the_docs_%s' % self.name

    def _create_workspace(self):
        workspace_name = self._get_workspace_name()
        filled_template = WORKSPACE_TEMPLATE.format(
                                                 client_name=workspace_name, 
                                                 owner='hrafng', 
                                                 depot_path=self.repo_url,
                                                 root=self.working_dir)

        ps = subprocess.Popen(['p4', 'client', '-i'], stdin=subprocess.PIPE)
        out, err = ps.communicate(filled_template)
        log.info(out)
        log.info(err)
        retcode = ps.wait()
        if retcode != 0:
            raise ProjectImportError("Could not create workspace '%s'" % workspace_name)


    def _sync(self):
        retcode = self.run('p4 -c %s sync' % _get_workspace_name())
        if retcode != 0:
            raise ProjectImportError("Failed to sync client '%s'" % _get_workspace_name())
   
    def update(self):
        """
        If self.working_dir is already a valid local copy of the repository,
        update the repository, else create a new local copy of the repository.
        """
        self._create_workspace()
        self._sync()


