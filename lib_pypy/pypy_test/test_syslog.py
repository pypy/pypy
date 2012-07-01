from __future__ import absolute_import
# XXX very minimal test
from pypy.tool.lib_pypy import ctypes_cachedir, rebuild_one

def setup_module(mod):
    # Generates the resource cache
    rebuild_one(ctypes_cachedir.join('syslog.ctc.py'))


def test_syslog():
    from lib_pypy import syslog
    assert hasattr(syslog, 'LOG_ALERT')
