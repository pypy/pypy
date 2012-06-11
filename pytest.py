#!/usr/bin/env python
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

For more information, use pytest.py -h.
"""
__all__ = ['main']

# XXX hack for win64:
# This patch must stay here until the END OF STAGE 1
# When all tests work, this branch will be merged
# and the branch stage 2 is started, where we remove this patch.
import sys
if hasattr(sys, "maxint") and hasattr(sys, "maxsize"):
    if sys.maxint != sys.maxsize:
        sys.maxint = sys.maxsize
        import warnings
        warnings.warn("""\n
---> This win64 port is now in stage 1: sys.maxint was modified.
---> When pypy/__init__.py becomes empty again, we have reached stage 2.
""")

from _pytest.core import main, UsageError, _preloadplugins
from _pytest import core as cmdline
from _pytest import __version__

if __name__ == '__main__': # if run as a script or by 'python -m pytest'
    import os
    if len(sys.argv) == 1 and os.path.dirname(sys.argv[0]) in '.':
        print >> sys.stderr, __doc__
        sys.exit(2)

    #XXX: sync to upstream later
    import pytest_cov
    raise SystemExit(main(plugins=[pytest_cov]))
else:
    _preloadplugins() # to populate pytest.* namespace so help(pytest) works
