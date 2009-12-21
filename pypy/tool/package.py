#!/usr/bin/env python
""" A sample script that packages PyPy, provided that it's already built.
Usage:

package.py pypydir [name-of-archive]
"""

import autopath
import shutil
import sys
import py
import os
import fnmatch
import tarfile
from pypy.tool.udir import udir

if sys.version_info < (2,6): py.test.skip("requires 2.6 so far")

def ignore_patterns(*patterns):
    """Function that can be used as copytree() ignore parameter.

    Patterns is a sequence of glob-style patterns
    that are used to exclude files"""
    def _ignore_patterns(path, names):
        ignored_names = []
        for pattern in patterns:
            ignored_names.extend(fnmatch.filter(names, pattern))
        return set(ignored_names)
    return _ignore_patterns

class PyPyCNotFound(Exception):
    pass

def main(basedir, name='pypy-nightly'):
    basedir = py.path.local(basedir)
    pypy_c = basedir.join('pypy', 'translator', 'goal', 'pypy-c')
    if not pypy_c.check():
        raise PyPyCNotFound('Please compile pypy first, using translate.py')
    builddir = udir.ensure("build", dir=True)
    pypydir = builddir.ensure("pypy", dir=True)
    shutil.copytree(str(basedir.join('lib-python')),
                    str(pypydir.join('lib-python')),
                    ignore=ignore_patterns('.svn'))
    pypydir.ensure('pypy', dir=True)
    shutil.copytree(str(basedir.join('pypy', 'lib')),
                    str(pypydir.join('pypy', 'lib')),
                    ignore=ignore_patterns('.svn'))
    pypydir.ensure('bin', dir=True)
    shutil.copy(str(pypy_c), str(pypydir.join('bin', 'pypy-c')))
    old_dir = os.getcwd()
    try:
        os.chdir(str(builddir))
        os.system('tar cvjf ' + str(builddir.join(name + '.tar.bz2')) +
                  " pypy")
    finally:
        os.chdir(old_dir)
    return builddir # for tests

if __name__ == '__main__':
    if len(sys.argv) == 1 or len(sys.argv) > 3:
        print >>sys.stderr, __doc__
        sys.exit(1)
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        main(sys.argv[1], sys.argv[2])
