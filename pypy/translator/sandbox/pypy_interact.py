#! /usr/bin/env python

"""Interacts with a PyPy subprocess translated with --sandbox.

Usage:
    pypy_interact.py [options] <executable> <args...>

Options:
    --tmp=DIR     the real directory that corresponds to the virtual /tmp,
                  which is the virtual current dir (always read-only for now)
    --heapsize=N  limit memory usage to N bytes, or kilo- mega- giga-bytes
                  with the 'k', 'm' or 'g' suffix respectively.
                  ATM this only works with PyPy translated with Boehm or
                  the semispace or generation GCs.
    --timeout=N   limit execution time to N (real-time) seconds.
    --log=FILE    log all user input into the FILE

Note that you can get readline-like behavior with a tool like 'ledit',
provided you use enough -u options:

    ledit python -u pypy_interact.py pypy-c-sandbox -u
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

    def __init__(self, executable, arguments, tmpdir=None):
        self.executable = executable = os.path.abspath(executable)
        self.tmpdir = tmpdir
        super(PyPySandboxedProc, self).__init__([self.argv0] + arguments,
                                                executable=executable)

    def build_virtual_root(self):
        # build a virtual file system:
        # * can access its own executable
        # * can access the pure Python libraries
        # * can access the temporary usession directory as /tmp
        exclude = ['.pyc', '.pyo']
        if self.tmpdir is None:
            tmpdirnode = Dir({})
        else:
            tmpdirnode = RealDir(self.tmpdir, exclude=exclude)
        pypydist = os.path.dirname(os.path.abspath(autopath.pypydir))

        return Dir({
            'bin': Dir({
                'pypy-c': RealFile(self.executable),
                'lib-python': RealDir(os.path.join(pypydist, 'lib-python'),
                                      exclude=exclude),
                'pypy': Dir({
                    'lib': RealDir(os.path.join(pypydist, 'pypy', 'lib'),
                                   exclude=exclude),
                    }),
                }),
             'tmp': tmpdirnode,
             })


if __name__ == '__main__':
    from getopt import getopt      # and not gnu_getopt!
    options, arguments = getopt(sys.argv[1:], 't:h', 
                                ['tmp=', 'heapsize=', 'timeout=', 'log=',
                                 'help'])
    tmpdir = None
    timeout = None
    logfile = None
    extraoptions = []

    def help():
        print >> sys.stderr, __doc__
        sys.exit(2)

    for option, value in options:
        if option in ['-t', '--tmp']:
            value = os.path.abspath(value)
            if not os.path.isdir(value):
                raise OSError("%r is not a directory" % (value,))
            tmpdir = value
        elif option == '--heapsize':
            value = value.lower()
            if value.endswith('k'):
                bytes = int(value[:-1]) * 1024
            elif value.endswith('m'):
                bytes = int(value[:-1]) * 1024 * 1024
            elif value.endswith('g'):
                bytes = int(value[:-1]) * 1024 * 1024 * 1024
            else:
                bytes = int(value)
            if bytes <= 0:
                raise ValueError
            if bytes > sys.maxint:
                raise OverflowError("--heapsize maximum is %d" % sys.maxint)
            extraoptions[:0] = ['--heapsize', str(bytes)]
        elif option == '--timeout':
            timeout = int(value)
        elif option == '--log':
            logfile = value
        elif option in ['-h', '--help']:
            help()
        else:
            raise ValueError(option)

    if len(arguments) < 1:
        help()

    sandproc = PyPySandboxedProc(arguments[0], extraoptions + arguments[1:],
                                 tmpdir=tmpdir)
    if timeout is not None:
        sandproc.settimeout(timeout, interrupt_main=True)
    if logfile is not None:
        sandproc.setlogfile(logfile)
    try:
        sandproc.interact()
    finally:
        sandproc.kill()
