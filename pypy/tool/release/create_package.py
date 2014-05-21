#!/usr/bin/env python
""" A sample script that packages PyPy, provided that it's already built.
It uses 'pypy/goal/pypy-c' and parts of the rest of the working
copy.  Usage:

    package.py --base-dir pypy-base-dir [--options]

Usually you would do:   package.py --version-name pypy-VER-PLATFORM
The output is found in the directory from --builddir,
by default /tmp/usession-YOURNAME/build/.
"""

import shutil
import sys
import os
#Add toplevel repository dir to sys.path
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0,basedir)
import py
import fnmatch
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

class MissingDependenciesError(Exception):
    pass

def fix_permissions(dirname):
    if sys.platform != 'win32':
        os.system("chmod -R a+rX %s" % dirname)
        os.system("chmod -R g-w %s" % dirname)

def generate_license(base_file, options):
    with open(base_file) as fid:
        txt = fid.read()
    return txt

def create_cffi_import_libraries(pypy_c, options):
    modules = ['_sqlite3']
    subprocess.check_call([str(pypy_c), '-c', 'import _sqlite3'])
    if not sys.platform == 'win32':
        modules += ['_curses', 'syslog', 'gdbm', '_sqlite3']
    if not options.no_tk:
        modules.append(('_tkinter'))
    for module in modules:
        try:
            subprocess.check_call([str(pypy_c), '-c', 'import ' + module])
        except subprocess.CalledProcessError:
            print >>sys.stderr, """Building %{0} bindings failed.
You can either install development headers package or
add --without-{0} option to skip packaging binary CFFI extension.""".format(module)
            raise MissingDependenciesError(module)

def package(basedir, options):
    name = options.name
    if not name:
        name = 'pypy-nightly'
    rename_pypy_c = options.pypy_c
    override_pypy_c = options.override_pypy_c

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
    if not options.no_cffi:
        create_cffi_import_libraries(pypy_c, options)

    if sys.platform == 'win32' and not rename_pypy_c.lower().endswith('.exe'):
        rename_pypy_c += '.exe'
    binaries = [(pypy_c, rename_pypy_c)]
    #
    builddir = options.builddir
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
        # Can't rename a DLL: it is always called 'libpypy-c.dll'
        win_extras = ['libpypy-c.dll', 'libexpat.dll', 'sqlite3.dll',
                          'libeay32.dll', 'ssleay32.dll']
        if not options.no_tk:
            win_extras += ['tcl85.dll', 'tk85.dll']

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
        if not options.no_tk:
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
                raise MissingDependenciesError('Tk runtime')

    # Careful: to copy lib_pypy, copying just the hg-tracked files
    # would not be enough: there are also ctypes_config_cache/_*_cache.py.
    shutil.copytree(str(basedir.join('lib-python').join(STDLIB_VER)),
                    str(pypydir.join('lib-python').join(STDLIB_VER)),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~'))
    shutil.copytree(str(basedir.join('lib_pypy')),
                    str(pypydir.join('lib_pypy')),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~',
                                           '*.c', '*.o'))
    for file in ['README.rst',]:
        shutil.copy(str(basedir.join(file)), str(pypydir))
    for file in ['_testcapimodule.c', '_ctypes_test.c']:
        shutil.copyfile(str(basedir.join('lib_pypy', file)),
                        str(pypydir.join('lib_pypy', file)))
    license = generate_license(str(basedir.join('LICENSE')), options)
    with open(pypydir.join('LICENSE'), 'w') as LICENSE:
        LICENSE.write(license)
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
    fix_permissions(builddir)

    old_dir = os.getcwd()
    try:
        os.chdir(str(builddir))
        if not options.nostrip:
            for source, target in binaries:
                if sys.platform == 'win32':
                    pass
                elif sys.platform == 'darwin':
                    # 'strip' fun: see issue #587 for why -x
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
    if options.targetdir is not None:
        print "Copying %s to %s" % (archive, options.targetdir)
        shutil.copy(archive, options.targetdir)
    else:
        print "Ready in %s" % (builddir,)
    return builddir # for tests

def create_package(args):
    import argparse
    if sys.platform == 'win32':
        pypy_exe = 'pypy.exe'
        license_base = os.path.join(basedir,'../local') # as on buildbot YMMV
    else:
        pypy_exe = 'pypy'
        license_base = '/usr/share/doc'
    parser = argparse.ArgumentParser()
    parser.add_argument('--without-tk', dest='no_tk', action='store_true',
        help='build and package the cffi tkinter module')
    parser.add_argument('--without-cffi', dest='no_cffi', action='store_true',
        help='do not pre-import any cffi modules')
    parser.add_argument('--nostrip', dest='nostrip', action='store_true',
        help='do not strip the exe, making it ~10MB larger')
    parser.add_argument('--rename_pypy_c', dest='pypy_c', type=str, default=pypy_exe,
        help='target executable name, defaults to "pypy"')
    parser.add_argument('--archive-name', dest='name', type=str, default='',
        help='pypy-VER-PLATFORM')
    parser.add_argument('--license_base', type=str, default=license_base,
        help='where to start looking for third party upstream licensing info')
    parser.add_argument('--builddir', type=str, default='',
        help='tmp dir for packaging')
    parser.add_argument('--targetdir', type=str, default='',
        help='destination dir for archive')
    options = parser.parse_args(args)

    if os.environ.has_key("PYPY_PACKAGE_NOSTRIP"):
        options.nostrip = True

    if os.environ.has_key("PYPY_PACKAGE_WITHOUTTK"):
        options.tk = True
    if not options.builddir:
        # The import actually creates the udir directory
        from rpython.tool.udir import udir
        options.builddir = udir.ensure("build", dir=True)
    assert '/' not in options.rename_pypy_c
    package(basedir, options)

if __name__ == '__main__':
    import sys
    create_package(sys.args)
