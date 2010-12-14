import py
import os
from subprocess import Popen, PIPE
import pypy
pypydir = os.path.dirname(os.path.abspath(pypy.__file__))


def get_mercurial_info():
    '''Obtain Mercurial version information by invoking the 'hg' command.'''
    # TODO: support extracting from .hg_archival.txt

    pypyroot = os.path.abspath(os.path.join(pypydir, '..'))
    hgexe = py.path.local.sysfind('hg')

    if hgexe and os.path.isdir(os.path.join(pypyroot, '.hg')):
        env = dict(os.environ)
        # get Mercurial into scripting mode
        env['HGPLAIN'] = '1'
        # disable user configuration, extensions, etc.
        env['HGRCPATH'] = os.devnull

        p = Popen([str(hgexe), 'id', '-i', pypyroot], stdout=PIPE, env=env)
        hgid = p.stdout.read().strip()

        p = Popen([str(hgexe), 'id', '-t', pypyroot], stdout=PIPE, env=env)
        hgtag = p.stdout.read().strip().split()[0]

        if hgtag == 'tip':
            # use the branch instead
            p = Popen([str(hgexe), 'id', '-b', pypyroot], stdout=PIPE, env=env)
            hgtag = p.stdout.read().strip()

        return 'PyPy', hgtag, hgid
    else:
        return None
