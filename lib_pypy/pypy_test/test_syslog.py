from __future__ import absolute_import
# XXX very minimal test

from lib_pypy.ctypes_config_cache import rebuild
rebuild.rebuild_one('syslog.ctc.py')

from lib_pypy import syslog


def test_syslog():
    assert hasattr(syslog, 'LOG_ALERT')
