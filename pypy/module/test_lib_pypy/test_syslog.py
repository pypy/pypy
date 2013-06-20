from __future__ import absolute_import
import py
try:
    from lib_pypy import syslog
except ImportError:
    py.test.skip('no syslog on this platform')

# XXX very minimal test

from lib_pypy.ctypes_config_cache import rebuild
rebuild.rebuild_one('syslog.ctc.py')


def test_syslog():
    assert hasattr(syslog, 'LOG_ALERT')
