#! /usr/bin/env python
"""
PyPy Test runner interface
--------------------------

Running test_all.py is equivalent to running py.test
(either installed from the py lib package, or from ../py/bin/).

For more information, use test_all.py -h.
"""
import sys, os

if len(sys.argv) == 1 and os.path.dirname(sys.argv[0]) in '.':
    print >> sys.stderr, __doc__
    sys.exit(2)

if __name__ == '__main__':
    import tool.autopath
    import py
    py.cmdline.pytest()
