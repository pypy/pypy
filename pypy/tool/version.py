import py
import os
from subprocess import Popen, PIPE
import pypy
pypydir = os.path.dirname(os.path.abspath(pypy.__file__))

def get_repo_version_info(hgexe=None):
    '''Obtain version information by invoking the 'hg' or 'git' commands.'''
    # TODO: support extracting from .hg_archival.txt

    default_retval = 'PyPy', '?', '?'
    pypyroot = os.path.abspath(os.path.join(pypydir, '..'))

    def maywarn(err, repo_type='Mercurial'):
        if not err:
            return

        from pypy.tool.ansi_print import ansi_log
        log = py.log.Producer("version")
        py.log.setconsumer("version", ansi_log)
        log.WARNING('Errors getting %s information: %s' % (repo_type, err))

    # Try to see if we can get info from Git if hgexe is not specified.
    if not hgexe:
        if os.path.isdir(os.path.join(pypyroot, '.git')):
            gitexe = py.path.local.sysfind('git')
            if gitexe:
                try:
                    p = Popen(
                        [str(gitexe), 'rev-parse', 'HEAD'],
                        stdout=PIPE, stderr=PIPE, cwd=pypyroot
                        )
                except OSError, e:
                    maywarn(e, 'Git')
                    return default_retval
                if p.wait() != 0:
                    maywarn(p.stderr.read(), 'Git')
                    return default_retval
                revision_id = p.stdout.read().strip()[:12]
                p = Popen(
                    [str(gitexe), 'describe', '--tags', '--exact-match'],
                    stdout=PIPE, stderr=PIPE, cwd=pypyroot
                    )
                if p.wait() != 0:
                    p = Popen(
                        [str(gitexe), 'branch'], stdout=PIPE, stderr=PIPE,
                        cwd=pypyroot
                        )
                    if p.wait() != 0:
                        maywarn(p.stderr.read(), 'Git')
                        return 'PyPy', '?', revision_id
                    branch = '?'
                    for line in p.stdout.read().strip().split('\n'):
                        if line.startswith('* '):
                            branch = line[1:].strip()
                            if branch == '(no branch)':
                                branch = '?'
                            break
                    return 'PyPy', branch, revision_id
                return 'PyPy', p.stdout.read().strip(), revision_id

    # Fallback to trying Mercurial.
    if hgexe is None:
        hgexe = py.path.local.sysfind('hg')

    if not os.path.isdir(os.path.join(pypyroot, '.hg')):
        maywarn('Not running from a Mercurial repository!')
        return default_retval
    elif not hgexe:
        maywarn('Cannot find Mercurial command!')
        return default_retval
    else:
        env = dict(os.environ)
        # get Mercurial into scripting mode
        env['HGPLAIN'] = '1'
        # disable user configuration, extensions, etc.
        env['HGRCPATH'] = os.devnull

        try:
            p = Popen([str(hgexe), 'version', '-q'],
                      stdout=PIPE, stderr=PIPE, env=env)
        except OSError, e:
            maywarn(e)
            return default_retval

        if not p.stdout.read().startswith('Mercurial Distributed SCM'):
            maywarn('command does not identify itself as Mercurial')
            return default_retval

        p = Popen([str(hgexe), 'id', '-i', pypyroot],
                  stdout=PIPE, stderr=PIPE, env=env)
        hgid = p.stdout.read().strip()
        maywarn(p.stderr.read())
        if p.wait() != 0:
            hgid = '?'

        p = Popen([str(hgexe), 'id', '-t', pypyroot],
                  stdout=PIPE, stderr=PIPE, env=env)
        hgtags = [t for t in p.stdout.read().strip().split() if t != 'tip']
        maywarn(p.stderr.read())
        if p.wait() != 0:
            hgtags = ['?']

        if hgtags:
            return 'PyPy', hgtags[0], hgid
        else:
            # use the branch instead
            p = Popen([str(hgexe), 'id', '-b', pypyroot],
                      stdout=PIPE, stderr=PIPE, env=env)
            hgbranch = p.stdout.read().strip()
            maywarn(p.stderr.read())

            return 'PyPy', hgbranch, hgid
