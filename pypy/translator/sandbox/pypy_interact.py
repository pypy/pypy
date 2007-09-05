#! /usr/bin/env python

"""Interacts with a PyPy subprocess translated with --sandbox.

Usage:
    pypy_interact.py [options] <executable> <args...>

Options:
    --tmp=DIR     the real directory that corresponds to the virtual /tmp,
                  which is the virtual current dir (always read-only for now)
"""

import sys, os
import autopath
from pypy.translator.sandbox.sandlib import SimpleIOSandboxedProc
from pypy.translator.sandbox.sandlib import VirtualizedSandboxedProc
from pypy.translator.sandbox.vfs import Dir, RealDir, RealFile

class PyPySandboxedProc(VirtualizedSandboxedProc, SimpleIOSandboxedProc):
    debug = True
    argv0 = '/bin/pypy-c'
    virtual_cwd = '/tmp'
    virtual_env = {}
    virtual_console_isatty = True

    def __init__(self, executable, arguments, tmpdir):
        # build a virtual file system:
        # * can access its own executable
        # * can access the pure Python libraries
        # * can access the temporary usession directory as /tmp
        executable = os.path.abspath(executable)
        if tmpdir is None:
            tmpdirnode = Dir({})
        else:
            tmpdirnode = RealDir(tmpdir)
        pypydist = os.path.dirname(os.path.abspath(autopath.pypydir))

        virtual_root = Dir({
            'bin': Dir({
                'pypy-c': RealFile(executable),
                'lib-python': RealDir(os.path.join(pypydist, 'lib-python')),
                'pypy': Dir({
                    'lib': RealDir(os.path.join(pypydist, 'pypy', 'lib')),
                    }),
                }),
             'tmp': tmpdirnode,
             })

        super(PyPySandboxedProc, self).__init__(virtual_root,
                                                [self.argv0] + arguments,
                                                executable=executable)


if __name__ == '__main__':
    from getopt import getopt      # and not gnu_getopt!
    options, arguments = getopt(sys.argv[1:], 't:h', ['tmp=', 'help'])
    tmpdir = None

    def help():
        print >> sys.stderr, __doc__
        sys.exit(2)

    for option, value in options:
        if option in ['-t', '--tmp']:
            value = os.path.abspath(value)
            if not os.path.isdir(value):
                raise OSError("%r is not a directory" % (value,))
            tmpdir = value
        elif option in ['-h', '--help']:
            help()
        else:
            raise ValueError(option)

    if len(arguments) < 1:
        help()

    sandproc = PyPySandboxedProc(arguments[0], arguments[1:], tmpdir=tmpdir)
    sandproc.interact()
