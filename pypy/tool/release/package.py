#!/usr/bin/env python
from __future__ import print_function 
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
import platform
from pypy.tool.release.smartstrip import smartstrip
from pypy.tool.release.make_portable import make_portable


def get_arch():
    if sys.platform in ('win32', 'darwin'):
        return sys.platform
    else:
        return platform.uname()[-1]

ARCH = get_arch()


USE_ZIPFILE_MODULE = ARCH == 'win32'

STDLIB_VER = "2.7"

POSIX_EXE = 'pypy'

from lib_pypy.pypy_tools.build_cffi_imports import (create_cffi_import_libraries,
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
    if ARCH != 'win32':
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
        basename = POSIX_EXE + '-c'
        if ARCH == 'win32':
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
        failures = create_cffi_import_libraries(
            str(pypy_c), options, str(basedir),
            embed_dependencies=options.embed_dependencies,
        )

        for key, module in failures:
            print("""!!!!!!!!!!\nBuilding {0} bindings failed.
                You can either install development headers package,
                add the --without-{0} option to skip packaging this
                binary CFFI extension, or say --without-cffi.""".format(key),
                file=sys.stderr)
        if len(failures) > 0:
            return 1, None

    if ARCH == 'win32' and not rename_pypy_c.lower().endswith('.exe'):
        rename_pypy_c += '.exe'
    binaries = [(pypy_c, rename_pypy_c, None)]

    if (ARCH != 'win32' and    # handled below
        not _fake and os.path.getsize(str(pypy_c)) < 500000):
        # This 'pypy_c' is very small, so it means it relies on a so/dll
        # If it would be bigger, it wouldn't.  That's a hack.
        if ARCH.startswith('darwin'):
            ext = 'dylib'
        else:
            ext = 'so'
        libpypy_name = 'lib' + POSIX_EXE + '-c.' + ext
        libpypy_c = pypy_c.new(basename=libpypy_name)
        if not libpypy_c.check():
            raise PyPyCNotFound('Expected pypy to be mostly in %r, but did '
                                'not find it' % (str(libpypy_c),))
        binaries.append((libpypy_c, libpypy_name, None))
    #
    builddir = py.path.local(options.builddir)
    pypydir = builddir.ensure(name, dir=True)
    lib_pypy = pypydir.join('lib_pypy')
    # do not create lib_pypy yet, it will be created by the copytree below

    includedir = basedir.join('include')
    shutil.copytree(str(includedir), str(pypydir.join('include')))
    pypydir.ensure('include', dir=True)

    if ARCH == 'win32':
        os.environ['PATH'] = str(basedir.join('externals').join('bin')) + ';' + \
                            os.environ.get('PATH', '')
        src, tgt, _ = binaries[0]
        pypyw = src.new(purebasename=src.purebasename + 'w')
        if pypyw.exists():
            tgt = py.path.local(tgt)
            binaries.append((pypyw, tgt.new(purebasename=tgt.purebasename + 'w').basename, None))
            print("Picking %s" % str(pypyw))
        # Can't rename a DLL
        win_extras = [('lib' + POSIX_EXE + '-c.dll', None),
                      ('sqlite3.dll', lib_pypy)]
        if not options.no__tkinter:
            tkinter_dir = lib_pypy.join('_tkinter')
            win_extras += [('tcl85.dll', tkinter_dir), ('tk85.dll', tkinter_dir)]

        for extra,target_dir in win_extras:
            p = pypy_c.dirpath().join(extra)
            if not p.check():
                p = py.path.local.sysfind(extra)
                if not p:
                    print("%s not found, expect trouble if this "
                          "is a shared build" % (extra,))
                    continue
            print("Picking %s" % p)
            binaries.append((p, p.basename, target_dir))
        libsdir = basedir.join('libs')
        if libsdir.exists():
            print('Picking %s (and contents)' % libsdir)
            shutil.copytree(str(libsdir), str(pypydir.join('libs')))
        else:
            if not _fake:
                raise RuntimeError('"libs" dir with import library not found.')
            # XXX users will complain that they cannot compile capi (cpyext)
            # modules for windows, also embedding pypy (i.e. in cffi)
            # will fail.
            # Has the lib moved, was translation not 'shared', or are
            # there no exported functions in the dll so no import
            # library was created?
        if not options.no__tkinter:
            try:
                p = pypy_c.dirpath().join('tcl85.dll')
                if not p.check():
                    p = py.path.local.sysfind('tcl85.dll')
                    if p is None:
                        raise WindowsError("tcl85.dll not found")
                tktcldir = p.dirpath().join('..').join('lib')
                shutil.copytree(str(tktcldir), str(pypydir.join('tcl')))
            except WindowsError:
                print("Packaging Tk runtime failed. tk85.dll and tcl85.dll "
                      "found in %s, expecting to find runtime in %s directory "
                      "next to the dlls, as per build "
                      "instructions." %(p, tktcldir), file=sys.stderr)
                import traceback;traceback.print_exc()
                raise MissingDependenciesError('Tk runtime')

    print('* Binaries:', [source.relto(str(basedir))
                          for source, target, target_dir in binaries])

    # Careful: to copy lib_pypy, copying just the hg-tracked files
    # would not be enough: there are also build artifacts like cffi-generated
    # dynamic libs
    shutil.copytree(str(basedir.join('lib-python').join(STDLIB_VER)),
                    str(pypydir.join('lib-python').join(STDLIB_VER)),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~'))
    shutil.copytree(str(basedir.join('lib_pypy')), str(lib_pypy),
                    ignore=ignore_patterns('.svn', 'py', '*.pyc', '*~',
                                           '*_cffi.c', '*.o', '*.pyd-*', '*.obj',
                                           '*.lib', '*.exp', '*.manifest'))
    for file in ['README.rst',]:
        shutil.copy(str(basedir.join(file)), str(pypydir))
    for file in ['_testcapimodule.c', '_ctypes_test.c']:
        shutil.copyfile(str(basedir.join('lib_pypy', file)),
                        str(lib_pypy.join(file)))
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
    if ARCH == 'win32':
        bindir = pypydir
    else:
        bindir = pypydir.join('bin')
        bindir.ensure(dir=True)
    for source, target, target_dir in binaries:
        if target_dir:
            archive = target_dir.join(target)
        else:
            archive = bindir.join(target)
        if not _fake:
            shutil.copy(str(source), str(archive))
        else:
            open(str(archive), 'wb').close()
        os.chmod(str(archive), 0755)
    #if not _fake and not ARCH == 'win32':
    #    # create the pypy3 symlink
    #    old_dir = os.getcwd()
    #    os.chdir(str(bindir))
    #    try:
    #        os.symlink(POSIX_EXE, 'pypy3')
    #    finally:
    #        os.chdir(old_dir)
    fix_permissions(pypydir)

    old_dir = os.getcwd()
    try:
        os.chdir(str(builddir))
        if not _fake:
            for source, target, target_dir in binaries:
                if target_dir:
                    archive = target_dir.join(target)
                else:
                    archive = bindir.join(target)
                smartstrip(archive, keep_debug=options.keep_debug)

            # make the package portable by adding rpath=$ORIGIN/..lib,
            # bundling dependencies
            if options.make_portable:
                os.chdir(str(name))
                if not os.path.exists('lib'):
                    os.mkdir('lib')
                make_portable()
                os.chdir(str(builddir))
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
            if ARCH == 'darwin':
                print("Warning: tar on current platform does not suport "
                      "overriding the uid and gid for its contents. The tarball "
                      "will contain your uid and gid. If you are building the "
                      "actual release for the PyPy website, you may want to be "
                      "using another platform...", file=sys.stderr)
                e = os.system('tar --numeric-owner -cvjf ' + archive + " " + name)
            elif sys.platform.startswith('freebsd'):
                e = os.system('tar --uname=root --gname=wheel -cvjf ' + archive + " " + name)
            elif sys.platform == 'cygwin':
                e = os.system('tar --owner=Administrator --group=Administrators --numeric-owner -cvjf ' + archive + " " + name)
            else:
                e = os.system('tar --owner=root --group=root --numeric-owner -cvjf ' + archive + " " + name)
            if e:
                raise OSError('"tar" returned exit status %r' % e)
    finally:
        os.chdir(old_dir)
    if options.targetdir:
        print("Copying %s to %s" % (archive, options.targetdir))
        shutil.copy(archive, options.targetdir)
    else:
        print("Ready in %s" % (builddir,))
    return retval, builddir # for tests

def package(*args, **kwds):
    import argparse

    class NegateAction(argparse.Action):
        def __init__(self, option_strings, dest, nargs=0, **kwargs):
            super(NegateAction, self).__init__(option_strings, dest, nargs,
                                               **kwargs)

        def __call__(self, parser, ns, values, option):
            setattr(ns, self.dest, option[2:4] != 'no')

    if ARCH == 'win32':
        pypy_exe = POSIX_EXE + '.exe'
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
    parser.add_argument('--no-keep-debug', dest='keep_debug',
                        action='store_false', help='do not keep debug symbols')
    parser.add_argument('--rename_pypy_c', dest='pypy_c', type=str, default=pypy_exe,
        help='target executable name, defaults to "%s"' % pypy_exe)
    parser.add_argument('--archive-name', dest='name', type=str, default='',
        help='pypy-VER-PLATFORM')
    parser.add_argument('--builddir', type=str, default='',
        help='tmp dir for packaging')
    parser.add_argument('--targetdir', type=str, default='',
        help='destination dir for archive')
    parser.add_argument('--override_pypy_c', type=str, default='',
        help='use as pypy3 exe instead of pypy/goal/pypy3-c')
    parser.add_argument('--embedded-dependencies', '--no-embedded-dependencies',
                        dest='embed_dependencies',
                        action=NegateAction,
                        default=(ARCH in ('darwin', 'aarch64')),
                        help='whether to embed dependencies in CFFI modules '
                        '(default on OS X)')
    parser.add_argument('--make-portable',
                        dest='make_portable',
                        action=NegateAction,
                        default=(ARCH in ('darwin',)),
                        help='make the package portable by shipping '
                            'dependent shared objects and mangling RPATH')
    options = parser.parse_args(args)

    if os.environ.has_key("PYPY_PACKAGE_NOKEEPDEBUG"):
        options.keep_debug = False
    if os.environ.has_key("PYPY_PACKAGE_WITHOUTTK"):
        options.no__tkinter = True
    if os.environ.has_key("PYPY_EMBED_DEPENDENCIES"):
        options.embed_dependencies = True
    elif os.environ.has_key("PYPY_NO_EMBED_DEPENDENCIES"):
        options.embed_dependencies = False
    if os.environ.has_key("PYPY_MAKE_PORTABLE"):
        options.make_portable = True
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
    if ARCH == 'win32':
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
