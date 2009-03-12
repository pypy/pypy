
import py
from pypy.jit.metainterp.test.test_slist import ListTests
from pypy.jit.backend.x86.support import c_meta_interp

class Jit386Mixin(object):
    @staticmethod
    def meta_interp(fn, args, **kwds):
        return c_meta_interp(fn, args, **kwds)

    def check_loops(self, *args, **kwds):
        pass

    def interp_operations(self, *args, **kwds):
        py.test.skip("using interp_operations")

class TestSList(Jit386Mixin, ListTests):
    # for the individual tests see
    # ====> ../../test/test_slist.py
    pass

