import py
from pypy.rpython.tool.rffi_platform import CompilationError


class BaseAppTest:
    spaceconfig = dict(usemodules=['_continuation'], continuation=True)

    def setup_class(cls):
        try:
            import pypy.rlib.rstacklet
        except CompilationError, e:
            py.test.skip("cannot import rstacklet: %s" % e)

