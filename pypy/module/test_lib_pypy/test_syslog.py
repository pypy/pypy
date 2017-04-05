from __future__ import absolute_import
import sys, py
try:
    from lib_pypy import syslog
except ImportError:
    py.test.skip('no syslog on this platform')
except AssertionError:
    if '__pypy__' in sys.builtin_module_names:
        raise
    py.test.skip('AssertionError during import (wrong cffi version?)')

# XXX very minimal test

def test_syslog():
    assert hasattr(syslog, 'LOG_ALERT')
