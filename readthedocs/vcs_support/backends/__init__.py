from . import bzr, hg, git, svn, p4

backend_cls = {
    'bzr': bzr.Backend,
    'launchpad': bzr.Backend,
    'svn': svn.Backend,
    'git': git.Backend,
    'hg': hg.Backend,
    'p4': p4.Backend,
}
