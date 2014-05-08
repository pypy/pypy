import py
from rpython.rtyper.lltypesystem import lltype
from rpython.memory.gc.incminimark import IncrementalMiniMarkGC
from test_direct import BaseDirectGCTest

S = lltype.GcForwardReference()
S.become(lltype.GcStruct('S', ('someInt', lltype.Signed)))

class PinningGCTest(BaseDirectGCTest):
    def test_simple(self):
        someIntValue = 100
        obj = self.malloc(S)
        obj.someInt = someIntValue
        self.gc.pin(obj)
        self.gc.collect() # obj should still live
        assert obj.someInt == someIntValue

class TestIncminimark(PinningGCTest):
    from rpython.memory.gc.incminimark import IncrementalMiniMarkGC as GCClass