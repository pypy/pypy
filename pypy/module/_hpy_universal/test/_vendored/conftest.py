import pytest
from .support import ExtensionCompiler

def pytest_addoption(parser):
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")

@pytest.fixture(scope='session')
def hpy_base_dir(request):
    from hpy.devel import get_base_dir
    return get_base_dir()

@pytest.fixture(params=['cpython', 'universal'])
def abimode(request):
    return request.param

@pytest.fixture
def compiler(request, tmpdir, abimode, hpy_base_dir):
    compiler_verbose = request.config.getoption('--compiler-v')
    return ExtensionCompiler(tmpdir, abimode, hpy_base_dir,
                             compiler_verbose=compiler_verbose)
