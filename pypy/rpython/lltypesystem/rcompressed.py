from pypy.tool.pairtype import pairtype
from pypy.rlib.objectmodel import we_are_translated
from pypy.config.translationoption import IS_64_BITS
from pypy.rpython.rmodel import Repr, inputconst
from pypy.rpython.lltypesystem import lltype, llmemory, rffi



def get_compressed_gcref_repr(rtyper, baserepr):
    # Return either the original baserepr, or another repr standing for
    # a HiddenGcRef32.  The idea is that we only get a HiddenGcRef32 for
    # fixed-sized structures (XXX that are not too big); thus this is only
    # for structures that gets allocated by the minimarkpage2 mmap()-
    # within-32GB-of-RAM.
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

    def __init__(self, mgr, baserepr):
        self.mgr = mgr
        self.baserepr = baserepr
        self.BASETYPE = self.baserepr.lowleveltype

    def convert_const(self, value):
        ptr = self.baserepr.convert_const(value)
        T = lltype.typeOf(ptr)
        assert T == self.BASETYPE
        return llmemory._hiddengcref32(llmemory.cast_ptr_to_adr(ptr))


class __extend__(pairtype(Repr, CompressedGcRefRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        assert r_from.lowleveltype.TO._gckind == 'gc'
        return llops.genop('hide_into_adr32', [v],
                           resulttype=llmemory.HiddenGcRef32)

class __extend__(pairtype(CompressedGcRefRepr, Repr)):
    def convert_from_to((r_from, r_to), v, llops):
        assert r_to.lowleveltype.TO._gckind == 'gc'
        return llops.genop('show_from_adr32', [v],
                           resulttype=r_to.lowleveltype)
