import pytest
from .support import ExtensionCompiler, DefaultExtensionTemplate,\
    PythonSubprocessRunner, HPyDebugCapture, make_hpy_abi_fixture
from hpy.debug.leakdetector import LeakDetector
from pathlib import Path

IS_VALGRIND_RUN = False

def pytest_addoption(parser):
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
def hpy_devel(request):
    from hpy.devel import HPyDevel
    return HPyDevel()

@pytest.fixture
def leakdetector(hpy_abi):
    """
    Automatically detect leaks when the hpy_abi == 'debug'
    """
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
