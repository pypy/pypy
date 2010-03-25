"""
Test the readline library on top of PyPy.  The following tests run
in the PyPy interpreter, itself running on top of CPython
"""

import py
from pypy.conftest import gettestobjspace
from pypy.rpython.tool import rffi_platform as platform

try:
    from pypy.module.readline import c_readline
except platform.CompilationError, e:
    py.test.skip(e)


class AppTestReadline:

    def setup_class(cls):
        # enable usage of the readline mixedmodule
        space = gettestobjspace(usemodules=('readline',))
        cls.space = space

    def test_basic_import(self):
        # this is interpreted by PyPy
        import readline 
        readline.readline
        # XXX test more
