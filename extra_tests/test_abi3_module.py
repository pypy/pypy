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


def win32_diagnosis():
    """Why the loader could not resolve an import of the .pyd.

    "The specified module could not be found" names nothing, so walk the
    chain cpyext relies on (api.py:load_mapping_dll): is python3.dll in the
    process, where is it on disk, does it load at all, and is loading it by
    hand enough to make the import work."""
    import ctypes
    import glob
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetModuleHandleW.restype = ctypes.c_void_p
    k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    k32.GetModuleFileNameW.restype = ctypes.c_uint
    k32.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p,
                                       ctypes.c_uint]

    def loaded(name):
        handle = k32.GetModuleHandleW(name)
        if not handle:
            return 'no'
        buf = ctypes.create_unicode_buffer(1024)
        if not k32.GetModuleFileNameW(handle, buf, len(buf)):
            return 'yes, path unknown'
        return buf.value

    lines = ['sys.executable = %s' % (sys.executable,),
             'sys.prefix = %s' % (sys.prefix,),
             'sys.base_prefix = %s' % (sys.base_prefix,)]
    for name in ('libpypy%d.%d-c.dll' % sys.version_info[:2], 'python3.dll'):
        lines.append('loaded %s: %s' % (name, loaded(name)))
    candidates = []
    for dirname in (os.path.dirname(sys.executable), sys.prefix,
                    sys.base_prefix, os.path.join(ROOT, 'pypy', 'goal'),
                    ROOT):
        for pattern in ('python3.dll', 'libpypy*-c.dll'):
            candidates.extend(glob.glob(os.path.join(dirname, pattern)))
    lines.append('on disk: %s' % (sorted(set(candidates)),))
    for dll in sorted(set(c for c in candidates
                          if os.path.basename(c).lower() == 'python3.dll')):
        try:
            ctypes.WinDLL(dll)
        except OSError as e:
            lines.append('WinDLL(%s): %s' % (dll, e))
            continue
        lines.append('WinDLL(%s): loaded' % (dll,))
        try:
            importlib.import_module(MODNAME)
        except ImportError as e:
            lines.append('  import after that: %s' % (e,))
        else:
            lines.append('  import after that: ok, so load_mapping_dll'
                         ' looked in the wrong directory')
    return '\n'.join(lines)


def _compile_distutils(outdir, libraries, extra_link_args):
    """Compile through distutils, like extra_tests/cffi_tests do.

    On Windows this is what finds the compiler: MSVCCompiler.initialize()
    runs the vswhere lookup and sets INCLUDE/LIB/PATH itself, so no vcvars
    shell is needed.  distutils comes from setuptools on Python >= 3.12,
    hence the import below (see lib_pypy/cffi/_shimmed_dist_utils.py)."""
    try:
        import setuptools         # noqa: F401 - provides distutils on 3.12+
    except ImportError:
        pass
    from distutils.ccompiler import new_compiler
    from distutils import sysconfig

    compiler = new_compiler()
    compiler.output_dir = outdir
    sysconfig.customize_compiler(compiler)
    objects = compiler.compile(
        [CSOURCE], include_dirs=[sysconfig.get_config_var('INCLUDEPY')])
    out = MODNAME + importlib.machinery.EXTENSION_SUFFIXES[0]
    compiler.link_shared_object(objects, out, libraries=libraries,
                                export_symbols=['PyInit_' + MODNAME],
                                extra_preargs=extra_link_args)
    return os.path.join(outdir, out)


def _compile_ccdriver(outdir, libraries, extra_link_args):
    """Fallback for a PyPy without setuptools: PyPy's own driver, which
    needs cl.exe already on PATH (PYPY_CC, or a vcvars shell)."""
    from pypy_tools._cffi_compile import compile_shared
    return compile_shared(CSOURCE, MODNAME, outdir, libraries=libraries,
                          extra_link_args=extra_link_args)


@pytest.fixture(scope='session')
def abi3_module(tmpdir_factory):
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
    try:
        built = _compile_distutils(outdir, libraries, extra_link_args)
    except ImportError:
        try:
            built = _compile_ccdriver(outdir, libraries, extra_link_args)
        except ImportError:
            pytest.skip('needs setuptools or lib_pypy/pypy_tools')
    suffix = abi3_suffix()
    if suffix not in importlib.machinery.EXTENSION_SUFFIXES:
        # an older build without abi3 import support: still exercise
        # the module, test_abi3_suffix_is_importable reports the gap
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    shutil.move(built, os.path.join(outdir, MODNAME + suffix))
    sys.path.insert(0, outdir)
    try:
        try:
            return importlib.import_module(MODNAME)
        except ImportError as e:
            if sys.platform != 'win32':
                raise
            raise ImportError('%s\n%s' % (e, win32_diagnosis())) from e
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
