import pytest
from .support import ExtensionCompiler

def pytest_addoption(parser):
    parser.addoption(
        "--correct", action="store_true",
        help="Test against headers installed through hpy_devel"
    )

@pytest.fixture(scope='session')
def hpy_include_dir(request):
    if request.config.getoption('--correct'):
        from hpy_devel import get_include
        return get_include()
    else:
        import os
        THIS_DIR = os.path.dirname(__file__)
        return os.path.join(THIS_DIR, '../hpy-api/hpy_devel/include')

@pytest.fixture(params=['cpython', 'universal'])
def abimode(request):
    return request.param

@pytest.fixture
def compiler(tmpdir, abimode, hpy_include_dir):
    return ExtensionCompiler(tmpdir, abimode, hpy_include_dir)
