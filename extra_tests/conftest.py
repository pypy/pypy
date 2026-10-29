import os
import sys
import pytest


def _cache_msvc_env():
    """Put the MSVC environment in os.environ once.

    distutils' _get_vc_env() runs 'cmd /c vcvarsall.bat && set' and caches
    nothing, and cffi builds a fresh compiler for every ffi.verify(), so this
    suite would spawn vcvarsall hundreds of times.  Querying it once and
    setting DISTUTILS_USE_SDK makes _get_vc_env() return os.environ instead.
    """
    if sys.platform != 'win32' or os.environ.get('DISTUTILS_USE_SDK'):
        return
    try:
        # the fast registry-based lookup; setuptools used to patch distutils
        # with it, but no longer does
        from setuptools.msvc import msvc14_get_vc_env
        env = msvc14_get_vc_env('x64' if sys.maxsize > 2 ** 32 else 'x86')
    except Exception:
        try:
            from setuptools._distutils._msvccompiler import (
                _get_vc_env, PLAT_TO_VCVARS)
            from setuptools._distutils.util import get_platform
            env = _get_vc_env(PLAT_TO_VCVARS[get_platform()])
        except Exception:
            return      # leave distutils to find the compiler by itself
    if not env.get('path') or not env.get('include') or not env.get('lib'):
        return
    for key, value in env.items():
        key = key.upper()
        if key in ('PATH', 'INCLUDE', 'LIB', 'LIBPATH'):
            existing = os.environ.get(key, '')
            if existing:
                value = value.rstrip(os.pathsep) + os.pathsep + existing
            os.environ[key] = value
    os.environ['DISTUTILS_USE_SDK'] = '1'


def get_marker(item, name):
    try:
        return item.get_closest_marker(name=name)
    except AttributeError:
        # pytest < 3.6
        return item.get_marker(name=name)


def pytest_runtest_setup(item):
    if get_marker(item, name='pypy_only'):
        if '__pypy__' not in sys.builtin_module_names:
            pytest.skip('PyPy-specific test')


def pytest_configure(config):
    config.addinivalue_line("markers", "pypy_only: PyPy-specific test")
    _cache_msvc_env()

# This needs to be in the top-level conftest.py, it is copied from the one
# in hpy_tests/_vendored See the note at
# https://docs.pytest.org/en/7.1.x/reference/reference.html#initialization-hooks
def pytest_addoption(parser):
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")
    parser.addoption(
        "--subprocess-v", action="store_true",
        help="Print to stdout the stdout and stderr of Python subprocesses"
             "executed via run_python_subprocess")
    parser.addoption(
        "--dump-dir",
        help="Enables dump mode and specifies where to write generated test "
             "sources. This will then only generate the sources and skip "
             "evaluation of the tests.")

def pytest_collection_modifyitems(config, items):
    skip1 = pytest.mark.skip(reason="PyPy does not warn")
    skip2 = pytest.mark.skip(reason="PyPy does not report a traceback")
    for item in items:
        if item.name == "test_more_buffer_warning":
            item.add_marker(skip1)
        if item.name == "test_callback_exception":
            item.add_marker(skip2)

