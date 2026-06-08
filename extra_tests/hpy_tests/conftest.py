import sys
import pytest

try:
    import _hpy_universal
    disable = False
except ImportError:
    disable = True

if sys.platform == "win32":
    disable = True


def pytest_ignore_collect(path, config):
    return disable


@pytest.fixture(scope='session')
def hpy_devel(tmp_path_factory):
    """
    Session-scoped HPyDevel.  If possible, compile the HPy runtime helper
    sources into a single static library up-front so that individual test
    extensions only need to link against it instead of recompiling those
    sources every time (mirrors hpy PR #379).
    """
    from hpy.devel import HPyDevel
    devel = HPyDevel()
    try:
        _build_static_lib(devel, 'universal', tmp_path_factory)
    except Exception as e:
        # If the static-lib build fails we fall back to per-test source
        # compilation.  Print a warning so the developer knows why tests
        # are slower than expected but do not abort the session.
        import warnings
        warnings.warn(
            "HPy static-lib build failed (%s); "
            "falling back to per-test source compilation." % e,
            stacklevel=1,
        )
    return devel


def _build_static_lib(hpy_devel, hpy_abi, tmp_path_factory):
    """
    Compile the HPy extra (helper) sources into a static archive and register
    it on *hpy_devel* so that ``get_static_libs(hpy_abi)`` returns it.

    The archive is placed under::

        <session-tmp>/hpy_staticlib/<hpy_abi>/lib<name>.a
    """
    import distutils.ccompiler
    import distutils.sysconfig

    base = tmp_path_factory.mktemp('hpy_staticlib', numbered=False)
    abi_dir = base / hpy_abi
    abi_dir.mkdir(parents=True, exist_ok=True)
    obj_dir = base / 'obj' / hpy_abi
    obj_dir.mkdir(parents=True, exist_ok=True)

    compiler = distutils.ccompiler.new_compiler()
    distutils.sysconfig.customize_compiler(compiler)

    include_dirs = hpy_devel.get_extra_include_dirs()
    include_dirs.append(str(hpy_devel.get_include_dir_forbid_python_h()))

    macros = [('HPY', None), ('HPY_ABI_UNIVERSAL', None)]

    objects = compiler.compile(
        hpy_devel.get_extra_sources(),
        output_dir=str(obj_dir),
        include_dirs=include_dirs,
        macros=macros,
    )

    lib_name = 'hpyextra'
    compiler.create_static_lib(objects, lib_name, output_dir=str(abi_dir))

    lib_filename = compiler.library_filename(lib_name, lib_type='static')
    hpy_devel._available_static_libs = {
        hpy_abi: [str(abi_dir / lib_filename)],
    }
