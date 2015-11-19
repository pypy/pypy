from email.parser import Parser

import py

import cffi
import pypy

egg_info = py.path.local(pypy.__file__)/'../../lib_pypy/cffi.egg-info/PKG-INFO'

def test_egg_version():
    info = Parser().parsestr(egg_info.read())
    assert info['version'] == cffi.__version__
