#!/usr/bin/env python
""" A sample script that packages PyPy, provided that it's already built.
It uses 'pypy/translator/goal/pypy-c' and parts of the rest of the working
copy.  Usage:

    package.py root-pypy-dir [name-of-archive] [name-of-pypy-c] [destination-for-tarball] [pypy-c-path]

Usually you would do:   package.py ../../.. pypy-VER-PLATFORM
The output is found in the directory /tmp/usession-YOURNAME/build/.
"""

import autopath
import shutil
import sys
import py
import os
import fnmatch
from pypy.tool.udir import udir

if sys.version_info < (2,6): py.test.skip("requires 2.6 so far")

USE_ZIPFILE_MODULE = sys.platform == 'win32'

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

def fix_permissions(basedir):
    if sys.platform != 'win32':
        os.system("chmod -R a+rX %s" % basedir)

def package(basedir, name='pypy-nightly', rename_pypy_c='pypy',
            copy_to_dir = None, override_pypy_c = None):
    basedir = py.path.local(basedir)
    if sys.platform == 'win32':
        # Can't rename a DLL
        if override_pypy_c is not None:
            rename_pypy_c = py.path.local(override_pypy_c).purebasename
            pypy_c_dir = py.path.local(override_pypy_c).dirname
        else:
            pypy_c_dir = basedir.join('pypy', 'translator', 'goal')
        pypy_c = pypy_c_dir.join('pypy-c.exe')
        libpypy_c = pypy_c_dir.join('libpypy-c.dll')
        libexpat = pypy_c_dir.join('libexpat.dll')
        if not libexpat.check():
            libexpat = py.path.local.sysfind('libexpat.dll')
            assert libexpat, "libexpat.dll not found"
        binaries = [(pypy_c, pypy_c.basename),
                    (libpypy_c, libpypy_c.basename),
                    (libexpat, libexpat.basename)]
    else:
        basename = 'pypy-c'
        if override_pypy_c is None:
            pypy_c = basedir.join('pypy', 'translator', 'goal', basename)
        else:
            pypy_c = py.path.local(override_pypy_c)
        binaries = [(pypy_c, rename_pypy_c)]
    if not pypy_c.check():
        print pypy_c
        raise PyPyCNotFound('Please compile pypy first, using translate.py')
    builddir = udir.ensure("build", dir=True)
    pypydir = builddir.ensure(name, dir=True)
    # Careful: to copy lib_pypy, copying just the svn-tracked files
    # would not be enough: there are also ctypes_config_cache/_*_cache.py.
    shutil.copytree(str(basedir.join('lib-python')),
                    str(pypydir.join('lib-python')),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~'))
    shutil.copytree(str(basedir.join('lib_pypy')),
                    str(pypydir.join('lib_pypy')),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~'))
    for file in ['LICENSE', 'README']:
        shutil.copy(str(basedir.join(file)), str(pypydir))
    pypydir.ensure('include', dir=True)
    # we want to put there all *.h and *.inl from trunk/include
    # and from pypy/_interfaces
    includedir = basedir.join('include')
    headers = includedir.listdir('*.h') + includedir.listdir('*.inl')
    for n in headers:
        shutil.copy(str(n), str(pypydir.join('include')))
    #
    spdir = pypydir.ensure('site-packages', dir=True)
    shutil.copy(str(basedir.join('site-packages', 'README')), str(spdir))
    #
    if sys.platform == 'win32':
        bindir = pypydir
    else:
        bindir = pypydir.join('bin')
        bindir.ensure(dir=True)
    for source, target in binaries:
        archive = bindir.join(target)
        shutil.copy(str(source), str(archive))
    old_dir = os.getcwd()
    fix_permissions(builddir)
    try:
        os.chdir(str(builddir))
        #
        # 'strip' fun: see https://codespeak.net/issue/pypy-dev/issue587
        for source, target in binaries:
            if sys.platform == 'win32':
                pass
            elif sys.platform == 'darwin':
                os.system("strip -x " + str(bindir.join(target)))    # ignore errors
            else:
                os.system("strip " + str(bindir.join(target)))    # ignore errors
        #
        if USE_ZIPFILE_MODULE:
            import zipfile
            archive = str(builddir.join(name + '.zip'))
            zf = zipfile.ZipFile(archive, 'w',
                                 compression=zipfile.ZIP_DEFLATED)
            for (dirpath, dirnames, filenames) in os.walk(name):
                for fnname in filenames:
                    filename = os.path.join(dirpath, fnname)
                    zf.write(filename)
            zf.close()
        else:
            archive = str(builddir.join(name + '.tar.bz2'))
            if sys.platform == 'darwin':
                e = os.system('tar --numeric-owner -cvjf ' + archive + " " + name)
            else:
                e = os.system('tar --owner=root --group=root --numeric-owner -cvjf ' + archive + " " + name)
            if e:
                raise OSError('"tar" returned exit status %r' % e)
    finally:
        os.chdir(old_dir)
    if copy_to_dir is not None:
        print "Copying %s to %s" % (archive, copy_to_dir)
        shutil.copy(archive, str(copy_to_dir))
    else:
        print "Ready in %s" % (builddir,)
    return builddir # for tests

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print >>sys.stderr, __doc__
        sys.exit(1)
    else:
        package(*sys.argv[1:])
