#! /usr/bin/env python
"""
Usage:  checkmodule.py <module-name>

Check annotation and rtyping of the PyPy extension module from
pypy/module/<module-name>/.  Useful for testing whether a
modules compiles without doing a full translation.
"""
import autopath
import sys

from pypy.objspace.fake.checkmodule import checkmodule

def main(argv):
    if len(argv) != 2:
        print >> sys.stderr, __doc__
        sys.exit(2)
    modname = argv[1]
    if modname in ('-h', '--help'):
        print >> sys.stderr, __doc__
        sys.exit(0)
    if modname.startswith('-'):
        print >> sys.stderr, "Bad command line"
        print >> sys.stderr, __doc__
        sys.exit(1)
    checkmodule(modname)
    print 'Passed.'

if __name__ == '__main__':
    main(sys.argv)
