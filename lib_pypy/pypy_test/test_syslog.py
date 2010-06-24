from __future__ import absolute_import
# XXX very minimal test

from ..ctypes_config_cache import rebuild
rebuild.rebuild_one('syslog.ctc.py')

from .. import syslog


def test_syslog():
    assert hasattr(syslog, 'LOG_ALERT')
