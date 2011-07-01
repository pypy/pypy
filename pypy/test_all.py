#! /usr/bin/env python
"""
PyPy Test runner interface
--------------------------

Running test_all.py is equivalent to running py.test
which you independently install, see
http://pytest.org/getting-started.html

For more information, use test_all.py -h.
"""
import sys, os
sys.orig_maxint = sys.maxint
sys.maxint = 2**63-1


if len(sys.argv) == 1 and os.path.dirname(sys.argv[0]) in '.':
    print >> sys.stderr, __doc__
    sys.exit(2)

if __name__ == '__main__':
    import tool.autopath
    import pytest
    sys.exit(pytest.main())
