from email.parser import Parser

import py
from urllib.request import urlopen

import cffi
import pypy

egg_info = py.path.local(pypy.__file__)/'../../lib_pypy/cffi.egg-info/PKG-INFO'

def test_egg_version():
    info = Parser().parsestr(egg_info.read())
    assert info['version'] == cffi.__version__

def test_pycparser_version():
    url = 'https://raw.githubusercontent.com/eliben/pycparser/master/pycparser/__init__.py'
    source = urlopen(url).read().decode('utf8')
    dest = py.path.local(__file__).join('..', '..', '..', 'lib_pypy', 'cffi',
                                        '_pycparser', '__init__.py').read()
    # if this fails, the vendored pycparser is not the latest version
    assert source.strip() == dest.strip()
