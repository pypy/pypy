import pytest
from .support import ExtensionCompiler

def pytest_addoption(parser):
    parser.addoption(
        "--correct", action="store_true",
        help="Test against headers installed through hpy_devel"
    )
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")


@pytest.fixture(scope='session')
def hpy_include_dir(request):
    if request.config.getoption('--correct'):
        from hpy.devel import get_include
        return get_include()
    else:
        import os
        THIS_DIR = os.path.dirname(__file__)
        return os.path.join(THIS_DIR, '../hpy/devel/include')

@pytest.fixture(params=['cpython', 'universal'])
def abimode(request):
    return request.param

@pytest.fixture
def compiler(request, tmpdir, abimode, hpy_include_dir):
    compiler_verbose = request.config.getoption('--compiler-v')
    return ExtensionCompiler(tmpdir, abimode, hpy_include_dir,
                             compiler_verbose=compiler_verbose)
