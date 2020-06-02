#!/usr/bin/env python

bundle = ['sqlite3', 'ssl', 'crypto', 'ffi', 'expat', 'tcl8', 'tk8', 'gdbm',
          'lzma', 'tinfo', 'tinfow', 'ncursesw', 'panelw', 'ncurses', 'panel',
          'panelw', 'intl', 'z', 'bz2']

import os
from os.path import dirname, relpath, join, exists, basename, realpath
from shutil import copy2, copytree
import sys
from glob import glob
from subprocess import check_output, check_call


def get_deps_darwin(binary):
    deps = {}
    output = check_output(['otool', '-L', binary])
    output = output.splitlines()
    output = output[1:]  # first line is binary name
    for line in output:
        path = line.strip().split()[0]
        if not path or path == binary:
            continue

        needed = basename(path)

        if needed[3:].split('.', 1)[0] not in bundle:
            continue

        deps[needed] = path
        deps.update(get_deps(path))

    return deps

def get_deps(binary):
    if sys.platform == 'darwin':
        return get_deps_darwin(binary)

    deps = {}
    output = check_output(['ldd', binary])
    for line in output.splitlines():
        if '=>' not in line:
            continue
        line = line.strip()
        needed, path = line.split(' => ')
        if path == 'not found':
            print('Broken dependency in ' + binary)
        path = path.split(' ')[0]
        if not path:
            continue

        if needed[3:].split('.', 1)[0] not in bundle:
            continue

        deps[needed] = path
        deps.update(get_deps(path))

    return deps


def gather_deps(binaries):
    deps = {}
    for binary in binaries:
        deps.update(get_deps(binary))

    return deps


def copy_deps(deps):
    copied = {}

    for needed, path in deps.items():
        bname = basename(path)

        copy2(realpath(path), 'lib/' + bname)
        copied[path] = 'lib/' + bname

        if not exists('lib/' + needed):
            os.symlink(bname, 'lib/' + needed)

    return copied


def rpath_binaries(binaries):
    rpaths = {}

    for binary in binaries:
        check_call(['chmod', 'a+w', binary])
        if sys.platform == 'darwin':
            rpath = join('@executable_path', relpath('lib', dirname(binary)))
            check_call(['install_name_tool', '-add_rpath', rpath, binary])

            # change path for deps, this deps call is sorta redundant, but we
            # don't have this dependency info in the passed in data...
            deps = get_deps(binary)
            for dep, path in deps.items():
                rpath = join('@rpath', dep)
                if rpath != path:
                    check_call(['install_name_tool', '-change', path, rpath, binary])
                    print('Set RPATH of {0} for {1} to {2}'.format(binary, path, rpath))

        else:
            rpath = join('$ORIGIN', relpath('lib', dirname(binary)))
            check_call(['patchelf', '--set-rpath', rpath, binary])

        rpaths[binary] = rpath

    return rpaths


def make_portable():
    ext = 'so'
    if sys.platform == 'darwin':
        ext = 'dylib'

    binaries = glob('bin/libpypy*.' + ext)
    if not binaries:
        raise ValueError('Could not find bin/libpypy*.%s in "%s"' % (ext, os.getcwd()))
    binaries.extend(glob('lib_pypy/*_cffi.pypy*.' + ext))
    binaries.extend(glob('lib_pypy/_pypy_openssl*.' + ext))
    binaries.extend(glob('lib_pypy/_tkinter/*_cffi.pypy*.' + ext))

    deps = gather_deps(binaries)

    copied = copy_deps(deps)

    for path, item in copied.items():
        print('Copied {0} to {1}'.format(path, item))

    if exists('/usr/share/tcl8.5'):
        copytree('/usr/share/tcl8.5', 'lib/tcl')
    if exists('/usr/share/tk8.5'):
        copytree('/usr/share/tk8.5', 'lib/tk')

    binaries.extend(copied.values())

    rpaths = rpath_binaries(binaries)
    for binary, rpath in rpaths.items():
        print('Set RPATH of {0} to {1}'.format(binary, rpath))

    return deps


if __name__ == '__main__':
    try:
        os.chdir(sys.argv[1])
    except:
        print('Call as %s <path/to/pypy/topdir' % sys.argv[0])
        exit(-1)

    try:
        os.mkdir('lib')
    except OSError:
        pass

    make_portable()

