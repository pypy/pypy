
# XXX very minimal test

from pypy.lib.ctypes_config_cache import rebuild
rebuild.rebuild_one('syslog.ctc.py')

from pypy.lib import syslog


def test_syslog():
    assert hasattr(syslog, 'LOG_ALERT')
