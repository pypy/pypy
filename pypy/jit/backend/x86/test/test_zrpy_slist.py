
import py
from pypy.jit.metainterp.test.test_slist import ListTests
from pypy.jit.backend.x86.runner import CPU386
from pypy.jit.backend.test.support import CCompiledMixin

class Jit386Mixin(CCompiledMixin):
    CPUClass = CPU386

class TestSList(Jit386Mixin, ListTests):
    # for the individual tests see
    # ====> ../../../test/test_slist.py
    pass

