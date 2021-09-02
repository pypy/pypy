import pytest
from .support import ExtensionCompiler
from hpy.debug.pytest import hpy_debug # make it available to all tests

@pytest.fixture(scope='session')
def hpy_devel(request):
    from hpy.devel import HPyDevel
    return HPyDevel()

@pytest.fixture(params=['universal', 'debug'])
def hpy_abi(request):
    return request.param

@pytest.fixture
def compiler(request, tmpdir, hpy_devel, hpy_abi):
    compiler_verbose = request.config.getoption('--compiler-v')
    return ExtensionCompiler(tmpdir, hpy_devel, hpy_abi,
                             compiler_verbose=compiler_verbose)
