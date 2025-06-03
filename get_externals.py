'''Get external dependencies for building PyPy
they will end up in the platform.host().basepath, something like repo-root/external
'''

from __future__ import print_function

import argparse
import os
import shutil
import sys
import zipfile
from subprocess import Popen, PIPE, check_call
from rpython.translator.platform import host

def checkout_repo(dest='externals', org='pypy', branch='default', verbose=False):
    url = 'https://github.com/{}/externals'.format(org)
    if os.path.exists(dest):
        if os.path.exists(os.path.join(dest, ".git")):
            cmd = ['git', '-C', dest, 'pull', url]
        else:
            # remove a mercurial clone
            shutil.rmtree(dest)
            cmd = ['git','clone',url, dest]
    else:
        cmd = ['git','clone',url, dest]
    check_call(cmd, verbose)
    cmd = ['git','-C', dest, 'checkout',branch]
    check_call(cmd)

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
