import py
from pypy.conftest import gettestobjspace
from pypy.rpython.tool.rffi_platform import CompilationError


class BaseAppTest:
    def setup_class(cls):
        try:
            import pypy.rlib.rstacklet
        except CompilationError, e:
            py.test.skip("cannot import rstacklet: %s" % e)
        cls.space = gettestobjspace(usemodules=['_continuation'], continuation=True)
