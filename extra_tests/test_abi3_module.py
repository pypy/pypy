"""Check that a cp312-abi3 extension loads and runs.

lib_pypy/_abi3_test.c is compiled with Py_LIMITED_API 3.12, installed under
the abi3 extension suffix and imported by name, so the import hook has to
find it.  On Windows it links python3.lib only, like a CPython-built abi3
wheel, so a successful import also proves the python3.dll forwarders resolve.
"""
import importlib
import importlib.machinery
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSOURCE = os.path.join(ROOT, 'lib_pypy', '_abi3_test.c')
MODNAME = '_abi3_test'


def abi3_suffix():
    """What a CPython abi3 wheel's module file is called here."""
    if sys.platform == 'win32':
        return '.pyd'
    return '.abi3.so'


def find_python3_lib():
    for libdir in (os.path.join(sys.base_prefix, 'libs'),
                   os.path.join(ROOT, 'libs'),
                   os.path.join(ROOT, 'pypy', 'goal')):
        if os.path.exists(os.path.join(libdir, 'python3.lib')):
            return os.path.join(libdir, 'python3')
    return None


@pytest.fixture(scope='session')
def abi3_module(tmpdir_factory):
    try:
        from pypy_tools._cffi_compile import compile_shared
    except ImportError:
        pytest.skip('needs lib_pypy/pypy_tools')
    libraries = extra_link_args = None
    if sys.platform == 'win32':
        python3 = find_python3_lib()
        if python3 is None:
            pytest.skip('no python3.lib, build predates the mapping dll')
        # import from python3.dll alone: pyconfig.h names pythonXY.lib in a
        # #pragma, so that one must be excluded explicitly
        libraries = [python3]
        extra_link_args = [
            '/NODEFAULTLIB:python{0[0]}{0[1]}.lib'.format(sys.version_info)]
    outdir = str(tmpdir_factory.mktemp('abi3'))
    built = compile_shared(CSOURCE, MODNAME, outdir, libraries=libraries,
                           extra_link_args=extra_link_args)
    suffix = abi3_suffix()
    if suffix not in importlib.machinery.EXTENSION_SUFFIXES:
        # an older build without abi3 import support: still exercise
        # the module, test_abi3_suffix_is_importable reports the gap
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    shutil.move(built, os.path.join(outdir, MODNAME + suffix))
    sys.path.insert(0, outdir)
    try:
        return importlib.import_module(MODNAME)
    finally:
        sys.path.remove(outdir)
        sys.modules.pop(MODNAME, None)


def test_abi3_suffix_is_importable():
    assert abi3_suffix() in importlib.machinery.EXTENSION_SUFFIXES


def test_built_with_limited_api(abi3_module):
    assert abi3_module.limited_api_version() == 0x030c0000


def test_multiply(abi3_module):
    assert abi3_module.multiply([1, 2, 3], [4, 5, 6]) == [4, 10, 18]
    assert abi3_module.multiply([], []) == []
    assert abi3_module.multiply((2, 3), (4, 5)) == [8, 15]
    big = list(range(1000))
    assert abi3_module.multiply(big, big) == [i * i for i in big]


def test_multiply_errors(abi3_module):
    with pytest.raises(ValueError):
        abi3_module.multiply([1, 2], [1])
    with pytest.raises(TypeError):
        abi3_module.multiply([1, 'x'], [1, 2])
    with pytest.raises(TypeError):
        abi3_module.multiply(1, 2)
