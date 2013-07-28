from rpython.jit.metainterp import typesystem
from rpython.rtyper.lltypesystem import lltype, llmemory


class TypeSystemTests(object):

    def test_ref_dict(self):
        d = self.helper.new_ref_dict()
        ref1 = self.fresh_ref()
        ref2 = self.fresh_ref()
        ref3 = self.fresh_ref()
        d[ref1] = 123
        d[ref2] = 456
        d[ref3] = 789
        ref1b = self.duplicate_ref(ref1)
        ref2b = self.duplicate_ref(ref2)
        ref3b = self.duplicate_ref(ref3)
        assert d[ref1b] == 123
        assert d[ref2b] == 456
        assert d[ref3b] == 789


class TestLLtype(TypeSystemTests):
    helper = typesystem.llhelper

    def fresh_ref(self):
        S = lltype.GcStruct('S')
        s = lltype.malloc(S)
        return lltype.cast_opaque_ptr(llmemory.GCREF, s)

    def duplicate_ref(self, x):
        s = x._obj.container._as_ptr()
        return lltype.cast_opaque_ptr(llmemory.GCREF, s)

    def null_ref(self):
        return lltype.nullptr(llmemory.GCREF.TO)
