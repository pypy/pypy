from __future__ import absolute_import
import os
import pytest
from pypy.tool.lib_pypy import ctypes_cachedir, rebuild_one


def setup_module(mod):
    # Generates the resource cache
    rebuild_one(ctypes_cachedir.join('resource.ctc.py'))
    if not hasattr(os, 'fork'):
        pytest.skip("can't test wait without fork")


def test_os_wait3():
    #XXX: have skip_if deco
    if not hasattr(os, 'wait3'):
        pytest.skip('no os.wait3')

    from lib_pypy._pypy_wait import wait3
    exit_status = 0x33

    child = os.fork()
    if child == 0: # in child
        os._exit(exit_status)
    else:
        pid, status, rusage = wait3(0)
        assert child == pid
        assert os.WIFEXITED(status)
        assert os.WEXITSTATUS(status) == exit_status
        assert isinstance(rusage.ru_utime, float)
        assert isinstance(rusage.ru_maxrss, int)

def test_os_wait4():
    #XXX: have skip_if deco
    if not hasattr(os, 'wait4'):
        pytest.skip('no os.wait4')

    from lib_pypy._pypy_wait import wait4
    exit_status = 0x33

    child = os.fork()
    if child == 0: # in child
        os._exit(exit_status)
    else:
        pid, status, rusage = wait4(child, 0)
        assert child == pid
        assert os.WIFEXITED(status)
        assert os.WEXITSTATUS(status) == exit_status
        assert isinstance(rusage.ru_utime, float)
        assert isinstance(rusage.ru_maxrss, int)
