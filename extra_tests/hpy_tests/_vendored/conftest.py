import pytest
from .support import ExtensionCompiler, DefaultExtensionTemplate,\
    PythonSubprocessRunner, HPyDebugCapture
from hpy.debug.leakdetector import LeakDetector

IS_VALGRIND_RUN = False

def pytest_addoption(parser):
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")
    parser.addoption(
        "--subprocess-v", action="store_true",
        help="Print to stdout the stdout and stderr of Python subprocesses"
             "executed via run_python_subprocess")


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    global IS_VALGRIND_RUN
    IS_VALGRIND_RUN = config.pluginmanager.hasplugin('valgrind_checker')
    config.addinivalue_line(
        "markers", "syncgc: Mark tests that rely on a synchronous GC."
    )

@pytest.fixture(scope='session')
def hpy_devel(request):
    from hpy.devel import HPyDevel
    return HPyDevel()

@pytest.fixture(params=['cpython', 'universal', 'debug'])
def hpy_abi(request):
    abi = request.param
    if abi == 'debug':
        with LeakDetector():
            yield abi
    else:
        yield abi

@pytest.fixture
def ExtensionTemplate():
    return DefaultExtensionTemplate


@pytest.fixture
def compiler(request, tmpdir, hpy_devel, hpy_abi, ExtensionTemplate):
    compiler_verbose = request.config.getoption('--compiler-v')
    return ExtensionCompiler(tmpdir, hpy_devel, hpy_abi,
                             compiler_verbose=compiler_verbose,
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
