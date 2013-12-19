#!/usr/bin/env python
""" A sample script that packages PyPy, provided that it's already built.
It uses 'pypy/goal/pypy-c' and parts of the rest of the working
copy.  Usage:

    package.py [--nostrip] [--without-tk] root-pypy-dir [name-of-archive] [name-of-pypy-c] [destination-for-tarball] [pypy-c-path]

Usually you would do:   package.py ../../.. pypy-VER-PLATFORM
The output is found in the directory /tmp/usession-YOURNAME/build/.
"""

import shutil
import sys
import os
#Add toplevel repository dir to sys.path
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import py
import fnmatch
from rpython.tool.udir import udir
import subprocess

if sys.version_info < (2,6): py.test.skip("requires 2.6 so far")

USE_ZIPFILE_MODULE = sys.platform == 'win32'

STDLIB_VER = "2.7"

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
        os.system("chmod -R g-w %s" % basedir)

def package(basedir, name='pypy-nightly', rename_pypy_c='pypy',
            copy_to_dir=None, override_pypy_c=None, nostrip=False,
            withouttk=False):
    assert '/' not in rename_pypy_c
    basedir = py.path.local(basedir)
    if override_pypy_c is None:
        basename = 'pypy-c'
        if sys.platform == 'win32':
            basename += '.exe'
        pypy_c = basedir.join('pypy', 'goal', basename)
    else:
        pypy_c = py.path.local(override_pypy_c)
    if not pypy_c.check():
        print pypy_c
        if os.path.isdir(os.path.dirname(str(pypy_c))):
            raise PyPyCNotFound(
                'Please compile pypy first, using translate.py,'
                ' or check that you gave the correct path'
                ' (see docstring for more info)')
        else:
            raise PyPyCNotFound(
                'Bogus path: %r does not exist (see docstring for more info)'
                % (os.path.dirname(str(pypy_c)),))
    win_extras = ['libpypy-c.dll', 'libexpat.dll', 'sqlite3.dll',
                      'libeay32.dll', 'ssleay32.dll']
    subprocess.check_call([str(pypy_c), '-c', 'import _sqlite3'])
    if not sys.platform == 'win32':
        subprocess.check_call([str(pypy_c), '-c', 'import _curses'])
        subprocess.check_call([str(pypy_c), '-c', 'import syslog'])
    if not withouttk:
        try:
            subprocess.check_call([str(pypy_c), '-c', 'import _tkinter'])
        except subprocess.CalledProcessError:
            print >>sys.stderr, """Building Tk bindings failed.
You can either install Tk development headers package or
add --without-tk option to skip packaging binary CFFI extension."""
            sys.exit(1)
        #Can the dependencies be found from cffi somehow?    
        win_extras += ['tcl85.dll', 'tk85.dll']    
    if sys.platform == 'win32' and not rename_pypy_c.lower().endswith('.exe'):
        rename_pypy_c += '.exe'
    binaries = [(pypy_c, rename_pypy_c)]
    #
    builddir = udir.ensure("build", dir=True)
    pypydir = builddir.ensure(name, dir=True)
    includedir = basedir.join('include')
    # Recursively copy all headers, shutil has only ignore
    # so we do a double-negative to include what we want
    def copyonly(dirpath, contents):
        return set(contents) - set(
            shutil.ignore_patterns('*.h', '*.incl')(dirpath, contents),
        )
    shutil.copytree(str(includedir), str(pypydir.join('include')))
    pypydir.ensure('include', dir=True)

    if sys.platform == 'win32':
        #Don't include a mscvrXX.dll, users should get their own.
        #Instructions are provided on the website.

        # Can't rename a DLL: it is always called 'libpypy-c.dll'

        for extra in win_extras:
            p = pypy_c.dirpath().join(extra)
            if not p.check():
                p = py.path.local.sysfind(extra)
                if not p:
                    print "%s not found, expect trouble if this is a shared build" % (extra,)
                    continue
            print "Picking %s" % p
            binaries.append((p, p.basename))
        importlib_name = 'python27.lib'    
        if pypy_c.dirpath().join(importlib_name).check():
            shutil.copyfile(str(pypy_c.dirpath().join(importlib_name)),
                        str(pypydir.join('include/python27.lib')))
            print "Picking %s as %s" % (pypy_c.dirpath().join(importlib_name),
                        pypydir.join('include/python27.lib'))
        else:
            pass
            # XXX users will complain that they cannot compile cpyext
            # modules for windows, has the lib moved or are there no
            # exported functions in the dll so no import library is created?
        if not withouttk:
            try:
                p = pypy_c.dirpath().join('tcl85.dll')
                if not p.check():
                    p = py.path.local.sysfind('tcl85.dll')
                tktcldir = p.dirpath().join('..').join('lib')
                shutil.copytree(str(tktcldir), str(pypydir.join('tcl')))
            except WindowsError:
                print >>sys.stderr, """Packaging Tk runtime failed.
tk85.dll and tcl85.dll found, expecting to find runtime in ..\\lib
directory next to the dlls, as per build instructions."""
                import traceback;traceback.print_exc()
                sys.exit(1)

    # Careful: to copy lib_pypy, copying just the hg-tracked files
    # would not be enough: there are also ctypes_config_cache/_*_cache.py.
    shutil.copytree(str(basedir.join('lib-python').join(STDLIB_VER)),
                    str(pypydir.join('lib-python').join(STDLIB_VER)),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~'))
    shutil.copytree(str(basedir.join('lib_pypy')),
                    str(pypydir.join('lib_pypy')),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~',
                                           '*.c', '*.o'))
    for file in ['LICENSE', 'README.rst']:
        shutil.copy(str(basedir.join(file)), str(pypydir))
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
        # 'strip' fun: see issue #587
        if not nostrip:
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
            if sys.platform == 'darwin' or sys.platform.startswith('freebsd'):
                print >>sys.stderr, """Warning: tar on current platform does not suport overriding the uid and gid
for its contents. The tarball will contain your uid and gid. If you are
building the actual release for the PyPy website, you may want to be
using another platform..."""
                e = os.system('tar --numeric-owner -cvjf ' + archive + " " + name)
            elif sys.platform == 'cygwin':
                e = os.system('tar --owner=Administrator --group=Administrators --numeric-owner -cvjf ' + archive + " " + name)
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


def print_usage():
    print >>sys.stderr, __doc__
    sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print_usage()

    args = sys.argv[1:]
    kw = {}

    for i, arg in enumerate(args):
        if arg == '--nostrip':
            kw['nostrip'] = True
        elif arg == '--without-tk':
            kw['withouttk'] = True
        elif not arg.startswith('--'):
            break
        else:
            print_usage()

    if os.environ.has_key("PYPY_PACKAGE_NOSTRIP"):
        kw['nostrip'] = True

    if os.environ.has_key("PYPY_PACKAGE_WITHOUTTK"):
        kw['withouttk'] = True

    args = args[i:]
    package(*args, **kw)
