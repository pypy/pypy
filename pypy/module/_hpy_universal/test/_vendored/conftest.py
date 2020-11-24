import pytest
import sys
from .support import ExtensionCompiler

disable = False

if sys.platform == 'win32':
    # skip all tests on windows, see issue hpyproject/hpy#61
    disable = True

def pytest_ignore_collect(path, config):
    if disable:
        return True

def pytest_collect_file(path, parent):
    if disable:
        # We end up here when calling py.test .../test_foo.py directly
        # It's OK to kill the whole session with the following line
        pytest.skip("skipping on windows")

def pytest_addoption(parser):
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")

@pytest.fixture(scope='session')
def hpy_devel(request):
    from hpy.devel import HPyDevel
    return HPyDevel()

@pytest.fixture(params=['cpython', 'universal'])
def hpy_abi(request):
    return request.param

@pytest.fixture
def compiler(request, tmpdir, hpy_devel, hpy_abi):
    compiler_verbose = request.config.getoption('--compiler-v')
    return ExtensionCompiler(tmpdir, hpy_devel, hpy_abi,
                             compiler_verbose=compiler_verbose)
