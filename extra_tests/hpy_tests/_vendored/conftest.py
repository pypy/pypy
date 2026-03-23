import pytest
from .support import ExtensionCompiler, DefaultExtensionTemplate,\
    PythonSubprocessRunner, HPyDebugCapture, make_hpy_abi_fixture
from pathlib import Path

IS_VALGRIND_RUN = False

# addoption only works in a top-level conftest file
def _pytest_addoption(parser):
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")
    parser.addoption(
        "--subprocess-v", action="store_true",
        help="Print to stdout the stdout and stderr of Python subprocesses "
             "executed via run_python_subprocess")
    parser.addoption(
        "--dump-dir",
        help="Enables dump mode and specifies where to write generated test "
             "sources. This will then only generate the sources and skip "
             "evaluation of the tests.")
    parser.addoption(
        '--reuse-venv', action="store_true",
        help="Development only: reuse the venv for test_distutils.py instead of "
             "creating a new one for every test")


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    global IS_VALGRIND_RUN
    IS_VALGRIND_RUN = config.pluginmanager.hasplugin('valgrind_checker')
    config.addinivalue_line(
        "markers", "syncgc: Mark tests that rely on a synchronous GC."
    )

# this is the default set of hpy_abi for all the tests. Individual files and
# classes can override it.
hpy_abi = make_hpy_abi_fixture('default')


@pytest.fixture(scope='session')
def hpy_devel(tmp_path_factory):
    from hpy.devel import HPyDevel
    import distutils.ccompiler
    import distutils.sysconfig
    devel = HPyDevel()
    try:
        hpy_abi = 'universal'
        base = tmp_path_factory.mktemp('hpy_staticlib', numbered=False)
        abi_dir = base / hpy_abi
        abi_dir.mkdir(parents=True, exist_ok=True)
        obj_dir = base / 'obj' / hpy_abi
        obj_dir.mkdir(parents=True, exist_ok=True)
        compiler = distutils.ccompiler.new_compiler()
        distutils.sysconfig.customize_compiler(compiler)
        include_dirs = devel.get_extra_include_dirs()
        include_dirs.append(str(devel.get_include_dir_forbid_python_h()))
        objects = compiler.compile(
            devel.get_extra_sources(),
            output_dir=str(obj_dir),
            include_dirs=include_dirs,
            macros=[('HPY', None), ('HPY_ABI_UNIVERSAL', None)],
        )
        lib_name = 'hpyextra'
        compiler.create_static_lib(objects, lib_name, output_dir=str(abi_dir))
        lib_filename = compiler.library_filename(lib_name, lib_type='static')
        lib_path = str(abi_dir / lib_filename)
        devel._available_static_libs = {
            'universal': [lib_path],
            'hybrid': [lib_path],
        }
    except Exception as e:
        import warnings
        warnings.warn(
            "HPy static-lib build failed (%s); "
            "falling back to per-test source compilation." % e,
            stacklevel=1,
        )
    return devel

@pytest.fixture
def leakdetector(hpy_abi):
    """
    Automatically detect leaks when the hpy_abi == 'debug'
    """
    from hpy.debug.leakdetector import LeakDetector
    if 'debug' in hpy_abi:
        with LeakDetector() as ld:
            yield ld
    else:
        yield None

@pytest.fixture
def ExtensionTemplate():
    return DefaultExtensionTemplate

@pytest.fixture
def compiler(request, tmpdir, hpy_devel, hpy_abi, ExtensionTemplate):
    compiler_verbose = request.config.getoption('--compiler-v')
    dump_dir = request.config.getoption('--dump-dir')
    if dump_dir:
        # Test-specific dump dir in format: dump_dir/[mod_][cls_]func
        qname_parts = []
        if request.module:
            qname_parts.append(request.module.__name__)
        if request.cls:
            qname_parts.append(request.cls.__name__)
        qname_parts.append(request.function.__name__)
        test_dump_dir = "_".join(qname_parts).replace(".", "_")
        dump_dir = Path(dump_dir).joinpath(test_dump_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)
    return ExtensionCompiler(tmpdir, hpy_devel, hpy_abi,
                             compiler_verbose=compiler_verbose,
                             dump_dir=dump_dir,
                             ExtensionTemplate=ExtensionTemplate)


@pytest.fixture(scope="session")
def fatal_exit_code(request):
    import sys
    return {
        "linux": -6,  # SIGABRT
        # See https://bugs.python.org/issue36116#msg336782 -- the
        # return code from abort on Windows 8+ is a stack buffer overrun.
        # :|
        "win32": 0xC0000409,  # STATUS_STACK_BUFFER_OVERRUN
    }.get(sys.platform, -6)


@pytest.fixture
def python_subprocess(request, hpy_abi):
    verbose = request.config.getoption('--subprocess-v')
    yield PythonSubprocessRunner(verbose, hpy_abi)


@pytest.fixture()
def hpy_debug_capture(request, hpy_abi):
    assert hpy_abi == 'debug'
    with HPyDebugCapture() as reporter:
        yield reporter
