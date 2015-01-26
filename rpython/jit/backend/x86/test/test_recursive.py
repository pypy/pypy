
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.metainterp.test.test_recursive import RecursiveTests
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.backend.llsupport import asmmemmgr
from rpython.jit.backend.llsupport.asmmemmgr import unpack_traceback
from rpython.jit.metainterp.test.support import get_stats

class TestRecursive(Jit386Mixin, RecursiveTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_recursive.py
    def check_get_unique_id(self):            
        codemaps = asmmemmgr._memmngr.jit_codemap[:] # ups, sorting later
        assert len(codemaps) == 3
        codemaps.sort(lambda arg0, arg1: cmp(arg0[1], arg1[1]))
        # biggest is the big loop, smallest is the bridge
        assert unpack_traceback(codemaps[1][0]) == []
        # XXX very specific ASM addresses, very fragile test, but what we can
        #     do, really? 64bit only so far
        assert unpack_traceback(codemaps[0][0]) == [2]
        assert unpack_traceback(codemaps[1][0] + 100) == [2]
        assert unpack_traceback(codemaps[2][0] + 100) == [4]
        assert unpack_traceback(codemaps[2][0] + 200) == [4, 2]
        assert unpack_traceback(codemaps[2][0] + 500) == [4, 2]
        assert unpack_traceback(codemaps[2][0] + 380) == [4]
