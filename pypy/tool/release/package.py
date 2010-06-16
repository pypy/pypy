#!/usr/bin/env python
""" A sample script that packages PyPy, provided that it's already built.
Usage:

package.py pypydir [name-of-archive] [name-of-pypy-c]
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

def package(basedir, name='pypy-nightly', rename_pypy_c='pypy-c',
         override_pypy_c = None):
    basedir = py.path.local(basedir)
    if override_pypy_c is None:
        pypy_c = basedir.join('pypy', 'translator', 'goal', 'pypy-c')
    else:
        pypy_c = py.path.local(override_pypy_c)
    if not pypy_c.check():
        raise PyPyCNotFound('Please compile pypy first, using translate.py')
    builddir = udir.ensure("build", dir=True)
    pypydir = builddir.ensure(name, dir=True)
    shutil.copytree(str(basedir.join('lib-python')),
                    str(pypydir.join('lib-python')),
                    ignore=ignore_patterns('.svn', '*.pyc', '*~'))
    # Careful: to copy pypy/lib, copying just the svn-tracked files
    # would not be enough: there are also ctypes_config_cache/_*_cache.py.
    pypydir.ensure('pypy', dir=True)
    shutil.copytree(str(basedir.join('pypy', 'lib')),
                    str(pypydir.join('pypy', 'lib')),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~'))
    for file in ['LICENSE', 'README']:
        shutil.copy(str(basedir.join(file)), str(pypydir))
    pypydir.ensure('bin', dir=True)
    archive_pypy_c = pypydir.join('bin', rename_pypy_c)
    shutil.copy(str(pypy_c), str(archive_pypy_c))
    old_dir = os.getcwd()
    try:
        os.chdir(str(builddir))
        os.system("strip " + str(archive_pypy_c))
        os.system('tar cvjf ' + str(builddir.join(name + '.tar.bz2')) +
                  " " + name)
    finally:
        os.chdir(old_dir)
    return builddir # for tests

if __name__ == '__main__':
    if len(sys.argv) == 1 or len(sys.argv) > 4:
        print >>sys.stderr, __doc__
        sys.exit(1)
    else:
        package(*sys.argv[1:])
