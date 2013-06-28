from __future__ import absolute_import
import py
try:
    from lib_pypy import syslog
except ImportError:
    py.test.skip('no syslog on this platform')

# XXX very minimal test

def test_syslog():
    assert hasattr(syslog, 'LOG_ALERT')
