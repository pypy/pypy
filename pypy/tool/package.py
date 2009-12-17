#!/usr/bin/env python
""" A sample script that packages PyPy, provided that it's already built
"""

import autopath
import shutil
import sys
import py
import os
import tarfile
from pypy.tool.udir import udir

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
                    ignore=shutil.ignore_patterns('.svn'))
    pypydir.ensure('pypy', dir=True)
    shutil.copytree(str(basedir.join('pypy', 'lib')),
                    str(pypydir.join('pypy', 'lib')),
                    ignore=shutil.ignore_patterns('.svn'))
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
    main(sys.argv[1])
