import py
import os
from subprocess import Popen, PIPE
import pypy
pypydir = os.path.dirname(os.path.abspath(pypy.__file__))

def get_mercurial_info(hgexe=None):
    '''Obtain Mercurial version information by invoking the 'hg' command.'''
    # TODO: support extracting from .hg_archival.txt

    pypyroot = os.path.abspath(os.path.join(pypydir, '..'))
    if hgexe is None:
        hgexe = py.path.local.sysfind('hg')

    def maywarn(err):
        if not err:
            return

        from pypy.tool.ansi_print import ansi_log
        log = py.log.Producer("version")
        py.log.setconsumer("version", ansi_log)
        log.WARNING('Errors getting Mercurial information: ' + err)

    if not os.path.isdir(os.path.join(pypyroot, '.hg')):
        maywarn('Not running from a Mercurial repository!')
        return 'PyPy', '', ''
    elif not hgexe:
        maywarn('Cannot find Mercurial command!')
        return 'PyPy', '', ''
    else:
        env = dict(os.environ)
        # get Mercurial into scripting mode
        env['HGPLAIN'] = '1'
        # disable user configuration, extensions, etc.
        env['HGRCPATH'] = os.devnull

        p = Popen([str(hgexe), 'id', '-i', pypyroot],
                  stdout=PIPE, stderr=PIPE, env=env)
        hgid = p.stdout.read().strip()
        maywarn(p.stderr.read())

        p = Popen([str(hgexe), 'id', '-t', pypyroot],
                  stdout=PIPE, stderr=PIPE, env=env)
        hgtags = [t for t in p.stdout.read().strip().split() if t != 'tip']
        maywarn(p.stderr.read())

        if hgtags:
            return 'PyPy', hgtags[0], hgid
        else:
            # use the branch instead
            p = Popen([str(hgexe), 'id', '-b', pypyroot],
                      stdout=PIPE, stderr=PIPE, env=env)
            hgbranch = p.stdout.read().strip()
            maywarn(p.stderr.read())

            return 'PyPy', hgbranch, hgid
