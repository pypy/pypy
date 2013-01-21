#! /usr/bin/env python
"""
PyPy Test runner interface
--------------------------

Running pytest.py starts py.test, the testing tool
we use in PyPy.  It is distributed along with PyPy,
but you may get more information about it at
http://pytest.org/.

Note that it makes no sense to run all tests at once.
You need to pick a particular subdirectory and run

    cd pypy/.../test
    ../../../pytest.py [options]

For more information, use test_all.py -h.
"""
import sys, os


if __name__ == '__main__':
    if len(sys.argv) == 1 and os.path.dirname(sys.argv[0]) in '.':
        print >> sys.stderr, __doc__
        sys.exit(2)

    import pytest
    import pytest_cov
    sys.exit(pytest.main(plugins=[pytest_cov]))
