from rpython.rtyper.rmodel import Repr
from rpython.rtyper.lltypesystem import lltype, llmemory

from rpython.tool.pairtype import pairtype, extendabletype, pair

UNKNOWN = object()

class GCRefRepr(Repr):
    lowleveltype = llmemory.GCREF

    @staticmethod
    def make(r_base, cache):
        try:
            return cache[r_base]
        except KeyError:
            res = cache[r_base] = GCRefRepr(r_base)
            return res


    def __init__(self, r_base):
        self.r_base = r_base
        self._ll_eq_func = UNKNOWN
        self._ll_hash_func = UNKNOWN
        if hasattr(r_base, 'll_str'):
            ll_base_str = r_base.ll_str
            def ll_str(ptr):
                return ll_base_str(lltype.cast_opaque_ptr(r_base.lowleveltype, ptr))
            self.ll_str = ll_str

    def convert_const(self, x):
        return lltype.cast_opaque_ptr(llmemory.GCREF, self.r_base.convert_const(x))

    def get_ll_eq_function(self):
        if self._ll_eq_func is UNKNOWN:
            ll_base_eq_function = self.r_base.get_ll_eq_function()
            if ll_base_eq_function is None:
                ll_eq_func = None
            else:
                def ll_eq_func(ptr1, ptr2):
                    ptr1 = lltype.cast_opaque_ptr(self.r_base.lowleveltype, ptr1)
                    ptr2 = lltype.cast_opaque_ptr(self.r_base.lowleveltype, ptr2)
                    return ll_base_eq_function(ptr1, ptr2)
            self._ll_eq_func = ll_eq_func
        return self._ll_eq_func

    def get_ll_hash_function(self):
        if self._ll_hash_func is UNKNOWN:
            ll_base_hash_function = self.r_base.get_ll_hash_function()
            if ll_base_hash_function is None:
                ll_hash_func = None
            else:
                def ll_hash_func(ptr):
                    ptr = lltype.cast_opaque_ptr(self.r_base.lowleveltype, ptr)
                    return ll_base_hash_function(ptr)
            self._ll_hash_func = ll_hash_func
        return self._ll_hash_func

    def get_ll_dummyval_obj(self, rtyper, s_value):
        return DummyValueBuilderGCRef(rtyper)

class __extend__(pairtype(GCRefRepr, Repr)):
    def convert_from_to((r_from, r_to), v, llops):
        if isinstance(r_to.lowleveltype, lltype.Ptr) and r_to.lowleveltype.TO._gckind == 'gc':
            return llops.genop('cast_opaque_ptr', [v], r_to.lowleveltype)
        return NotImplemented

class __extend__(pairtype(Repr, GCRefRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from != r_to.r_base:
            v = pair(r_from, r_to.r_base).convert_from_to(v, llops)
        return llops.genop('cast_opaque_ptr', [v], r_to.lowleveltype)


class DummyValueBuilderGCRef(object):

    def __init__(self, rtyper):
        self.rtyper = rtyper

    def _freeze_(self):
        return True

    def __hash__(self):
        return hash(llmemory.GCREF)

    def __eq__(self, other):
        return (isinstance(other, DummyValueBuilderGCRef) and
                self.rtyper is other.rtyper)

    def __ne__(self, other):
        return not (self == other)

    @property
    def ll_dummy_value(self):
        try:
            return self.rtyper.cache_dummy_values[llmemory.GCREF]
        except KeyError:
            from rpython.rtyper import rclass
            from rpython.rtyper.rmodel import DummyValueBuilder
            rinstbase = rclass.getinstancerepr(self.rtyper, None)
            TYPE = rinstbase.lowleveltype
            val = DummyValueBuilder(self.rtyper, TYPE.TO).ll_dummy_value
            p = lltype.cast_opaque_ptr(llmemory.GCREF, val)
            self.rtyper.cache_dummy_values[llmemory.GCREF] = p
            return p


