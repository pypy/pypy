"""
conftest to run HPy tests after translation.

The HPy test files are located in pypy/module/_hpy_universal/test/_vendored,
and are copied directly from the main HPy repo. The conftest in _hpy_universal
takes care of automatically transforming the tests into AppTest.

Here, we want to run them DIRECTLY, since extra_tests are supposed to run on
top of a translated pypy. Ideally, it would be nice to tell pytest to collect
the files directory from the _vendored directory, but I couldn't find a way to
do it.

What we do instead is to physically copy the test files inside
extra_tests/hpy_tests/_vendored before the collection starts. Additionally, we
remove the original conftest and provide all the required fixtures here. In particular:

  - hpy_base_dir(): the default implementation relies on hpy.devel, but we
    don't have/don't want it installated. Instead, we fish the *.h and *.c
    files from _hpy_universal

  - abimode(): we want to test only the universal ABI
"""

import os.path
import py
import pytest
from pypy import pypydir

ROOT = py.path.local(__file__).dirpath()
TEST_SRC = py.path.local(pypydir).join('module', '_hpy_universal', 'test', '_vendored')
TEST_DST = ROOT.join('_vendored')

def pytest_sessionstart(session):
    if TEST_DST.check(exists=True):
        TEST_DST.remove()
    TEST_SRC.copy(TEST_DST)
    TEST_DST.join('conftest.py').remove()
    TEST_DST.join('README.txt').write("""
        WARNING: these files are automatically copied (and overwritten!)
        from _hpy_universal. Look at conftest.py for more details
    """)

def pytest_addoption(parser):
    parser.addoption(
        "--compiler-v", action="store_true",
        help="Print to stdout the commands used to invoke the compiler")

@pytest.fixture(scope='session')
def hpy_base_dir(request):
    from pypy.module._hpy_universal._vendored.hpy.devel import get_base_dir
    return str(get_base_dir())

@pytest.fixture
def abimode():
    return 'universal'

@pytest.fixture
def compiler(request, tmpdir, abimode, hpy_base_dir):
    from extra_tests.hpy_tests._vendored.support import ExtensionCompiler
    compiler_verbose = request.config.getoption('--compiler-v')
    return ExtensionCompiler(tmpdir, abimode, hpy_base_dir,
                             compiler_verbose=compiler_verbose)
