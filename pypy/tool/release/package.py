#!/usr/bin/env python
""" packages PyPy, provided that it's already built.
It uses 'pypy/goal/pypy-c' and parts of the rest of the working
copy.  Usage:

    package.py [--options] --archive-name=pypy-VER-PLATFORM

The output is found in the directory from --builddir,
by default /tmp/usession-YOURNAME/build/.

For a list of all options, see 'package.py --help'.
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
import glob

if sys.version_info < (2,6): py.test.skip("requires 2.6 so far")

USE_ZIPFILE_MODULE = sys.platform == 'win32'

STDLIB_VER = "3"

# XXX: don't hardcode the version
POSIX_EXE = 'pypy3.5'

from pypy.tool.build_cffi_imports import (create_cffi_import_libraries,
        MissingDependenciesError, cffi_build_scripts)

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

def fix_permissions(dirname):
    if sys.platform != 'win32':
        os.system("chmod -R a+rX %s" % dirname)
        os.system("chmod -R g-w %s" % dirname)


def pypy_runs(pypy_c, quiet=False):
    kwds = {}
    if quiet:
        kwds['stderr'] = subprocess.PIPE
    return subprocess.call([str(pypy_c), '-c', 'pass'], **kwds) == 0

def create_package(basedir, options, _fake=False):
    retval = 0
    name = options.name
    if not name:
        name = 'pypy-nightly'
    assert '/' not in name
    rename_pypy_c = options.pypy_c
    override_pypy_c = options.override_pypy_c

    basedir = py.path.local(basedir)
    if not override_pypy_c:
        basename = 'pypy-c'
        if sys.platform == 'win32':
            basename += '.exe'
        pypy_c = basedir.join('pypy', 'goal', basename)
    else:
        pypy_c = py.path.local(override_pypy_c)
    if not _fake and not pypy_c.check():
        raise PyPyCNotFound(
            'Expected but did not find %s.'
            ' Please compile pypy first, using translate.py,'
            ' or check that you gave the correct path'
            ' with --override_pypy_c' % pypy_c)
    if not _fake and not pypy_runs(pypy_c):
        raise OSError("Running %r failed!" % (str(pypy_c),))
    if not options.no_cffi:
        failures = create_cffi_import_libraries(pypy_c, options, basedir)
        for key, module in failures:
            print >>sys.stderr, """!!!!!!!!!!\nBuilding {0} bindings failed.
                You can either install development headers package,
                add the --without-{0} option to skip packaging this
                binary CFFI extension, or say --without-cffi.""".format(key)
        if len(failures) > 0:
            return 1, None

    if sys.platform == 'win32' and not rename_pypy_c.lower().endswith('.exe'):
        rename_pypy_c += '.exe'
    binaries = [(pypy_c, rename_pypy_c)]

    if (sys.platform != 'win32' and    # handled below
        not _fake and os.path.getsize(str(pypy_c)) < 500000):
        # This pypy-c is very small, so it means it relies on libpypy_c.so.
        # If it would be bigger, it wouldn't.  That's a hack.
        libpypy_name = ('libpypy-c.so' if not sys.platform.startswith('darwin')
                                       else 'libpypy-c.dylib')
        libpypy_c = pypy_c.new(basename=libpypy_name)
        if not libpypy_c.check():
            raise PyPyCNotFound('Expected pypy to be mostly in %r, but did '
                                'not find it' % (str(libpypy_c),))
        binaries.append((libpypy_c, libpypy_name))
    #
    builddir = py.path.local(options.builddir)
    pypydir = builddir.ensure(name, dir=True)

    includedir = basedir.join('include')
    shutil.copytree(str(includedir), str(pypydir.join('include')))
    pypydir.ensure('include', dir=True)

    if sys.platform == 'win32':
        src,tgt = binaries[0]
        pypyw = src.new(purebasename=src.purebasename + 'w')
        if pypyw.exists():
            tgt = py.path.local(tgt)
            binaries.append((pypyw, tgt.new(purebasename=tgt.purebasename + 'w').basename))
            print "Picking %s" % str(pypyw)
        # Can't rename a DLL: it is always called 'libpypy-c.dll'
        win_extras = ['libpypy-c.dll', 'sqlite3.dll']
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
        libsdir = basedir.join('libs')
        if libsdir.exists():
            print 'Picking %s (and contents)' % libsdir
            shutil.copytree(str(libsdir), str(pypydir.join('libs')))
        else:
            print '"libs" dir with import library not found.'
            print 'You have to create %r' % (str(libsdir),)
            print 'and copy libpypy-c.lib in there, renamed to python32.lib'
            # XXX users will complain that they cannot compile capi (cpyext)
            # modules for windows, also embedding pypy (i.e. in cffi)
            # will fail.
            # Has the lib moved, was translation not 'shared', or are
            # there no exported functions in the dll so no import
            # library was created?
        if not options.no_tk:
            try:
                p = pypy_c.dirpath().join('tcl85.dll')
                if not p.check():
                    p = py.path.local.sysfind('tcl85.dll')
                    if p is None:
                        raise WindowsError("tcl85.dll not found")
                tktcldir = p.dirpath().join('..').join('lib')
                shutil.copytree(str(tktcldir), str(pypydir.join('tcl')))
            except WindowsError:
                print >>sys.stderr, """Packaging Tk runtime failed.
tk85.dll and tcl85.dll found, expecting to find runtime in ..\\lib
directory next to the dlls, as per build instructions."""
                import traceback;traceback.print_exc()
                raise MissingDependenciesError('Tk runtime')

    print '* Binaries:', [source.relto(str(basedir))
                          for source, target in binaries]

    # Careful: to copy lib_pypy, copying just the hg-tracked files
    # would not be enough: there are also ctypes_config_cache/_*_cache.py.
    # XXX ^^^ this is no longer true!
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
    # Use original LICENCE file
    base_file = str(basedir.join('LICENSE'))
    with open(base_file) as fid:
        license = fid.read()
    with open(str(pypydir.join('LICENSE')), 'w') as LICENSE:
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
        if not _fake:
            shutil.copy(str(source), str(archive))
        else:
            open(str(archive), 'wb').close()
        os.chmod(str(archive), 0755)
    if not _fake and not sys.platform == 'win32':
        # create the pypy3 symlink
        old_dir = os.getcwd()
        os.chdir(str(bindir))
        try:
            os.symlink(POSIX_EXE, 'pypy3')
        finally:
            os.chdir(old_dir)
    fix_permissions(pypydir)

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
    if options.targetdir:
        print "Copying %s to %s" % (archive, options.targetdir)
        shutil.copy(archive, options.targetdir)
    else:
        print "Ready in %s" % (builddir,)
    return retval, builddir # for tests

def package(*args, **kwds):
    try:
        import argparse
    except ImportError:
        import imp
        argparse = imp.load_source('argparse', 'lib-python/2.7/argparse.py')
    if sys.platform == 'win32':
        pypy_exe = 'pypy.exe'
    else:
        pypy_exe = POSIX_EXE
    parser = argparse.ArgumentParser()
    args = list(args)
    if args:
        args[0] = str(args[0])
    else:
        args.append('--help')
    for key, module in sorted(cffi_build_scripts.items()):
        if module is not None:
            parser.add_argument('--without-' + key,
                    dest='no_' + key,
                    action='store_true',
                    help='do not build and package the %r cffi module' % (key,))
    parser.add_argument('--without-cffi', dest='no_cffi', action='store_true',
        help='skip building *all* the cffi modules listed above')
    parser.add_argument('--nostrip', dest='nostrip', action='store_true',
        help='do not strip the exe, making it ~10MB larger')
    parser.add_argument('--rename_pypy_c', dest='pypy_c', type=str, default=pypy_exe,
        help='target executable name, defaults to "pypy"')
    parser.add_argument('--archive-name', dest='name', type=str, default='',
        help='pypy-VER-PLATFORM')
    parser.add_argument('--builddir', type=str, default='',
        help='tmp dir for packaging')
    parser.add_argument('--targetdir', type=str, default='',
        help='destination dir for archive')
    parser.add_argument('--override_pypy_c', type=str, default='',
        help='use as pypy exe instead of pypy/goal/pypy-c')
    options = parser.parse_args(args)

    if os.environ.has_key("PYPY_PACKAGE_NOSTRIP"):
        options.nostrip = True
    if os.environ.has_key("PYPY_PACKAGE_WITHOUTTK"):
        options.no_tk = True
    if not options.builddir:
        # The import actually creates the udir directory
        from rpython.tool.udir import udir
        options.builddir = udir.ensure("build", dir=True)
    else:
        # if a user provides a path it must be converted to a local file system path
        # otherwise ensure in create_package will fail
        options.builddir = py.path.local(options.builddir)
    assert '/' not in options.pypy_c
    return create_package(basedir, options, **kwds)


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        # Try to avoid opeing a dialog box if one of the
        # subprocesses causes a system error
        import ctypes
        winapi = ctypes.windll.kernel32
        SetErrorMode = winapi.SetErrorMode
        SetErrorMode.argtypes=[ctypes.c_int]

        SEM_FAILCRITICALERRORS = 1
        SEM_NOGPFAULTERRORBOX  = 2
        SEM_NOOPENFILEERRORBOX = 0x8000
        flags = SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
        #Since there is no GetErrorMode, do a double Set
        old_mode = SetErrorMode(flags)
        SetErrorMode(old_mode | flags)

    retval, _ = package(*sys.argv[1:])
    sys.exit(retval)
