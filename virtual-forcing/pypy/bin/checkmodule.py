#! /usr/bin/env python
"""
Usage:  checkmodule.py [-b backend] <module-name>

Compiles the PyPy extension module from pypy/module/<module-name>/
into a fake program which does nothing. Useful for testing whether a
modules compiles without doing a full translation. Default backend is cli.

WARNING: this is still incomplete: there are chances that the
compilation fails with strange errors not due to the module. If a
module is known to compile during a translation but don't pass
checkmodule.py, please report the bug (or, better, correct it :-).
"""
import autopath
import sys

from pypy.objspace.fake.checkmodule import checkmodule

def main(argv):
    try:
        assert len(argv) in (2, 4)
        if len(argv) == 2:
            backend = 'cli'
            modname = argv[1]
            if modname in ('-h', '--help'):
                print >> sys.stderr, __doc__
                sys.exit(0)
            if modname.startswith('-'):
                print >> sys.stderr, "Bad command line"
                print >> sys.stderr, __doc__
                sys.exit(1)
        else:
            _, b, backend, modname = argv
            assert b == '-b'
    except AssertionError:
        print >> sys.stderr, __doc__
        sys.exit(2)
    else:
        checkmodule(modname, backend, interactive=True)
        print 'Module compiled succesfully'

if __name__ == '__main__':
    main(sys.argv)
