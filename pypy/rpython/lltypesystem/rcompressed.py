from pypy.tool.pairtype import pairtype
from pypy.rlib.objectmodel import we_are_translated
from pypy.config.translationoption import IS_64_BITS
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.error import TyperError


def get_compressed_gcref_repr(rtyper, baserepr):
    # Return either the original baserepr, or another repr standing for
    # a HiddenGcRef32.  The idea is that we only get a HiddenGcRef32 for
    # fixed-sized structures; they get allocated by the minimarkpage2
    # mmap()-within-32GB-of-RAM.
    if baserepr.lowleveltype.TO._is_varsize():
        return baserepr
    try:
        comprmgr = rtyper.compressed_gcref_manager
    except AttributeError:
        comprmgr = rtyper.compressed_gcref_manager = ComprGcRefManager(rtyper)
    return comprmgr.get_compressed_gcref_repr(baserepr)


class ComprGcRefManager(object):
    def __init__(self, rtyper):
        assert IS_64_BITS                # this is only for 64-bits
        self.rtyper = rtyper
        self.comprgcreprs = {}

    def get_compressed_gcref_repr(self, baserepr):
        try:
            return self.comprgcreprs[baserepr]
        except KeyError:
            comprgcrepr = CompressedGcRefRepr(self, baserepr)
            self.comprgcreprs[baserepr] = comprgcrepr
            return comprgcrepr


class CompressedGcRefRepr(Repr):
    lowleveltype = llmemory.HiddenGcRef32
    ll_eq_function = None
    ll_hash_function = None
    ll_fasthash_function = None

    def __init__(self, mgr, baserepr):
        self.mgr = mgr
        self.baserepr = baserepr
        self.BASETYPE = self.baserepr.lowleveltype

    def convert_const(self, value):
        ptr = self.baserepr.convert_const(value)
        T = lltype.typeOf(ptr)
        assert T == self.BASETYPE
        return llop.hide_into_ptr32(self.lowleveltype, ptr)

    def get_ll_eq_function(self):
        if self.ll_eq_function is None:
            basefunc = self.baserepr.get_ll_eq_function()
            if basefunc is None:
                return None
            BASETYPE = self.BASETYPE
            #
            def ll_eq_function(x, y):
                x = llop.show_from_ptr32(BASETYPE, x)
                y = llop.show_from_ptr32(BASETYPE, y)
                return basefunc(x, y)
            #
            self.ll_eq_function = ll_eq_function
        return self.ll_eq_function

    def get_ll_hash_function(self):
        if self.ll_hash_function is None:
            basefunc = self.baserepr.get_ll_hash_function()
            BASETYPE = self.BASETYPE
            #
            def ll_hiddengcref32_hash(x):
                x = llop.show_from_ptr32(BASETYPE, x)
                return basefunc(x)
            #
            self.ll_hash_function = ll_hiddengcref32_hash
        return self.ll_hash_function

    def get_ll_fasthash_function(self):
        if self.ll_fasthash_function is None:
            basefunc = self.baserepr.get_ll_fasthash_function()
            if basefunc is None:
                return None
            BASETYPE = self.BASETYPE
            #
            def ll_hiddengcref32_fasthash(x):
                x = llop.show_from_ptr32(BASETYPE, x)
                return basefunc(x)
            #
            self.ll_fasthash_function = ll_hiddengcref32_hash
        return self.ll_fasthash_function

    def get_ll_dummyval_obj(self, rtyper, s_value):
        return DummyValueBuilder(rtyper)


class DummyValueBuilder(object):
    TYPE = llmemory.HiddenGcRef32
    def __init__(self, rtyper):
        self.rtyper = rtyper
    def _freeze_(self):
        return True
    def __hash__(self):
        return 42
    def __eq__(self, other):
        return (isinstance(other, DummyValueBuilder) and
                self.rtyper is other.rtyper)
    def __ne__(self, other):
        return not (self == other)

    def build_ll_dummy_value(self):
        TYPE = self.TYPE
        try:
            return self.rtyper.cache_dummy_values[TYPE]
        except KeyError:
            # generate a dummy ptr to an immortal placeholder struct
            p = lltype.malloc(lltype.GcStruct('dummy'), immortal=True)
            p = llop.hide_into_ptr32(TYPE, p)
            self.rtyper.cache_dummy_values[TYPE] = p
            return p
    ll_dummy_value = property(build_ll_dummy_value)


class __extend__(pairtype(Repr, CompressedGcRefRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        v2 = llops.convertvar(v, r_from, r_to.baserepr)
        return llops.genop('hide_into_ptr32', [v2],
                           resulttype=llmemory.HiddenGcRef32)

class __extend__(pairtype(CompressedGcRefRepr, Repr)):
    def convert_from_to((r_from, r_to), v, llops):
        v2 = llops.genop('show_from_ptr32', [v],
                         resulttype=r_from.BASETYPE)
        return llops.convertvar(v2, r_from.baserepr, r_to)
