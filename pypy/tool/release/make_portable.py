#!/usr/bin/env python

bundle = ['sqlite3', 'ssl', 'crypto', 'ffi', 'expat', 'tcl', 'tk', 'gdbm',
          'lzma', 'tinfo', 'tinfow', 'ncursesw', 'panelw', 'ncurses', 'panel', 'panelw']

import os
from os.path import dirname, relpath, join, exists, basename, realpath
from shutil import copy2
import sys
from glob import glob
from subprocess import check_output, check_call


def get_deps(binary):
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
        path = realpath(path)
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

        copy2(path, 'lib/' + bname)
        copied[path] = 'lib/' + bname

        if not exists('lib/' + needed):
            os.symlink(bname, 'lib/' + needed)

    return copied


def rpath_binaries(binaries):
    rpaths = {}

    for binary in binaries:
        rpath = join('$ORIGIN', relpath('lib', dirname(binary)))
        check_call(['patchelf', '--set-rpath', rpath, binary])

        rpaths[binary] = rpath

    return rpaths


def make_portable():
    binaries = glob('bin/libpypy*.so')
    if not binaries:
        raise ValueError('Could not find bin/libpypy*.so in "%s"' % os.getcwd())
    binaries.extend(glob('lib_pypy/*_cffi.pypy*.so'))
    binaries.extend(glob('lib_pypy/_pypy_openssl*.so'))
    binaries.extend(glob('lib_pypy/_tkinter/*_cffi.pypy*.so'))

    deps = gather_deps(binaries)

    copied = copy_deps(deps)

    for path, item in copied.items():
        print('Copied {0} to {1}'.format(path, item))

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

