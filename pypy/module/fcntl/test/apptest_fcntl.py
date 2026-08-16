# spaceconfig = {"usemodules": ["fcntl", "struct", "array", "select", "time"]}

import os
import sys

import pytest

if os.name != 'posix':
    pytest.skip("fcntl module only available on unix", allow_module_level=True)

import fcntl

darwin_only = pytest.mark.skipif(sys.platform != 'darwin',
                                 reason="macOS specific")


def maketemp(tmpdir, name):
    # tmpdir comes from the fixture of the same name in fixtures.py
    return open(os.path.join(tmpdir, name), 'w+b')


def test_constants():
    assert isinstance(fcntl.FASYNC, int)
    assert isinstance(fcntl.F_DUPFD_CLOEXEC, int)

    # open file description locks (linux >= 3.15, macOS)
    if sys.platform == 'darwin' or sys.platform.startswith('linux'):
        assert isinstance(fcntl.F_OFD_GETLK, int)
        assert isinstance(fcntl.F_OFD_SETLK, int)
        assert isinstance(fcntl.F_OFD_SETLKW, int)

    if sys.platform == 'darwin':
        assert fcntl.F_FULLFSYNC == 51
        assert fcntl.F_NOCACHE == 48
        assert fcntl.F_GETPATH == 50
    else:
        assert not hasattr(fcntl, 'F_FULLFSYNC')
        assert not hasattr(fcntl, 'F_NOCACHE')

    if sys.platform.startswith('linux'):
        for name in ['F_GETPIPE_SZ', 'F_SETPIPE_SZ', 'F_ADD_SEALS',
                     'F_GET_SEALS', 'F_SEAL_SEAL', 'F_SEAL_SHRINK',
                     'F_SEAL_GROW', 'F_SEAL_WRITE']:
            assert isinstance(getattr(fcntl, name), int), name
    else:
        assert not hasattr(fcntl, 'F_SEAL_SEAL')


def test_dupfd_cloexec(tmpdir):
    f = maketemp(tmpdir, 'dupfd_cloexec')
    try:
        fd = fcntl.fcntl(f, fcntl.F_DUPFD_CLOEXEC)
        try:
            assert fd != f.fileno()
            assert fcntl.fcntl(fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        finally:
            os.close(fd)
    finally:
        f.close()


@darwin_only
def test_fullfsync(tmpdir):
    f = maketemp(tmpdir, 'fullfsync')
    try:
        f.write(b"data")
        f.flush()
        assert fcntl.fcntl(f, fcntl.F_FULLFSYNC) == 0
        assert fcntl.fcntl(f.fileno(), fcntl.F_FULLFSYNC) == 0
    finally:
        f.close()


@darwin_only
def test_nocache(tmpdir):
    f = maketemp(tmpdir, 'nocache')
    try:
        assert fcntl.fcntl(f, fcntl.F_NOCACHE, 1) == 0
        assert fcntl.fcntl(f, fcntl.F_NOCACHE, 0) == 0
    finally:
        f.close()


@darwin_only
@pytest.mark.skipif(not hasattr(sys, 'pypy_translation_info'),
                    reason="untranslated, ll2ctypes cannot call the variadic "
                           "fcntl() with a char* argument on darwin")
def test_getpath(tmpdir):
    f = maketemp(tmpdir, 'getpath')
    try:
        expected = os.path.realpath(f.name).encode('utf-8')
        res = fcntl.fcntl(f, fcntl.F_GETPATH, bytes(len(expected)))
        assert res == expected
    finally:
        f.close()


@pytest.mark.skipif(not hasattr(fcntl, 'F_GETPIPE_SZ'),
                    reason="F_GETPIPE_SZ is linux specific")
def test_pipe_size():
    r, w = os.pipe()
    try:
        default = fcntl.fcntl(w, fcntl.F_GETPIPE_SZ)
        assert default > 0
        fcntl.fcntl(w, fcntl.F_SETPIPE_SZ, default * 2)
        assert fcntl.fcntl(w, fcntl.F_GETPIPE_SZ) >= default
    finally:
        os.close(r)
        os.close(w)
