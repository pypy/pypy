#!/usr/bin/env python
"""
unit and functional testing with Python.
"""
__all__ = ['main']

# XXX hack for win64:
# This patch must stay here until the END OF STAGE 1
# When all tests work, this branch will be merged
# and the branch stage 2 is started, where we remove this patch.
import sys
if hasattr(sys, "maxsize"):
    if sys.maxint <> sys.maxsize:
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
    #XXX: sync to upstream later
    import pytest_cov
    raise SystemExit(main(plugins=[pytest_cov]))
else:
    _preloadplugins() # to populate pytest.* namespace so help(pytest) works
