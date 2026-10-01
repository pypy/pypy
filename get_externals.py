'''Get external dependencies for building PyPy
they will end up in the platform.host().basepath, something like repo-root/external
'''

from __future__ import print_function

import argparse
import os
import shutil
import sys
import zipfile
from subprocess import Popen, PIPE, check_call, check_output
from rpython.translator.platform import host

def checkout_repo(dest='externals', org='pypy', branch='default', verbose=False):
    url = 'https://github.com/{}/externals'.format(org)

    def run(cmd):
        if verbose:
            print(' '.join(cmd))
        check_call(cmd)

    if os.path.exists(dest) and not os.path.exists(os.path.join(dest, '.git')):
        # remove a mercurial clone
        shutil.rmtree(dest)
    if os.path.exists(dest):
        # Fetch the branch explicitly: a bare 'git pull url' would merge the
        # remote's default branch into whatever is checked out, leaving
        # 'branch' at the revision it was first cloned at.
        run(['git', '-C', dest, 'fetch', url, branch])
        run(['git', '-C', dest, 'checkout', '-B', branch, 'FETCH_HEAD'])
    else:
        run(['git', 'clone', '--branch', branch, url, dest])
    head = check_output(['git', '-C', dest, 'log', '-1',
                         '--format=%H %cs %s'],
                        universal_newlines=True).strip()
    print('externals branch {} at {}'.format(branch, head))

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-O', '--organization',
                   help='Organization owning the deps repos', default='pypy')
    p.add_argument('-e', '--externals', default=host.externals,
                   help='directory in which to store dependencies',
                   )
    p.add_argument('-b', '--branch', default=host.externals_branch,
                   help='branch to check out',
                   )
    p.add_argument('-p', '--platform', default=None,
                   help='someday support cross-compilation, ignore for now',
                   )
    return p.parse_args()


def main():
    if sys.platform != "win32":
        print("only needed on windows")
    args = parse_args()
    checkout_repo(
        dest=args.externals,
        org=args.organization,
        branch=args.branch,
        verbose=args.verbose,
    )

if __name__ == '__main__':
    main()
