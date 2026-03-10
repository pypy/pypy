from email.parser import Parser

import py
from urllib.request import urlopen

import cffi
import pypy
import pytest

metadata = py.path.local(pypy.__file__)/'../../lib_pypy/cffi-1.18.0.dev0.dist-info/METADATA'

def test_metadata():
    info = Parser().parsestr(metadata.read())
    assert info['version'] == cffi.__version__

@pytest.skipif('sys.version_info[0] < 3', reason="upstream is python3-only")
def test_pycparser_version():
    url = 'https://raw.githubusercontent.com/eliben/pycparser/master/pycparser/__init__.py'
    source = urlopen(url).read().decode('utf8')
    dest = py.path.local(__file__).join('..', '..', '..', 'lib_pypy', 'cffi',
                                        '_pycparser', '__init__.py').read()
    # if this fails, the vendored pycparser is not the latest version
    # lib_pypy/cffi/_pycparser/README
    assert source.strip() == dest.strip()
