""" Contains a mechanism for turning any class instance and any integer into a
pointer-like thing. Gives full control over pointer tagging, i.e. there won't
be tag checks everywhere in the C code.

Usage:  erasestuff, unerasestuff = new_erasing_pair('stuff')

An erasestuff(x) object contains a reference to 'x'.  Nothing can be done with
this object, except calling unerasestuff(), which returns 'x' again.  The point
is that all erased objects can be mixed together, whether they are instances,
lists, strings, etc.  As a special case, an erased object can also be an
integer fitting into 31/63 bits, with erase_int() and unerase_int().

Warning: some care is needed to make sure that you call the unerase function
corresponding to the original creator's erase function.  Otherwise, segfault.
"""

import sys
from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.error import TyperError



def erase_int(x):
    assert isinstance(x, int)
    res = 2 * x + 1
    if res > sys.maxint or res < -sys.maxint - 1:
        raise OverflowError
    return Erased(x, _identity_for_ints)

def unerase_int(y):
    assert y._identity is _identity_for_ints
    assert isinstance(y._x, int)
    return y._x


class ErasingPairIdentity(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'ErasingPairIdentity(%r)' % self.name

    def _getdict(self, bk):
        try:
            dict = bk._erasing_pairs_tunnel
        except AttributeError:
            dict = bk._erasing_pairs_tunnel = {}
        return dict

    def enter_tunnel(self, bookkeeper, s_obj):
        dict = self._getdict(bookkeeper)
        s_previousobj, reflowpositions = dict.setdefault(
            self, (annmodel.s_ImpossibleValue, {}))
        s_obj = annmodel.unionof(s_previousobj, s_obj)
        if s_obj != s_previousobj:
            dict[self] = (s_obj, reflowpositions)
            for position in reflowpositions:
                bookkeeper.annotator.reflowfromposition(position)

    def leave_tunnel(self, bookkeeper):
        dict = self._getdict(bookkeeper)
        s_obj, reflowpositions = dict.setdefault(
            self, (annmodel.s_ImpossibleValue, {}))
        reflowpositions[bookkeeper.position_key] = True
        return s_obj

    def get_input_annotation(self, bookkeeper):
        dict = self._getdict(bookkeeper)
        s_obj, _ = dict[self]
        return s_obj

_identity_for_ints = ErasingPairIdentity("int")


def new_erasing_pair(name):
    identity = ErasingPairIdentity(name)

    def erase(x):
        return Erased(x, identity)

    def unerase(y):
        assert y._identity is identity
        return y._x

    class Entry(ExtRegistryEntry):
        _about_ = erase

        def compute_result_annotation(self, s_obj):
            identity.enter_tunnel(self.bookkeeper, s_obj)
            return SomeErased()

        def specialize_call(self, hop):
            bk = hop.rtyper.annotator.bookkeeper
            s_obj = identity.get_input_annotation(bk)
            return hop.r_result.rtype_erase(hop, s_obj)

    class Entry(ExtRegistryEntry):
        _about_ = unerase

        def compute_result_annotation(self, s_obj):
            assert SomeErased().contains(s_obj)
            return identity.leave_tunnel(self.bookkeeper)

        def specialize_call(self, hop):
            if hop.r_result.lowleveltype is lltype.Void:
                return hop.inputconst(lltype.Void, None)
            [v] = hop.inputargs(hop.args_r[0])
            return hop.args_r[0].rtype_unerase(hop, v)

    return erase, unerase

def new_static_erasing_pair(name):
    erase, unerase = new_erasing_pair(name)
    return staticmethod(erase), staticmethod(unerase)


# ---------- implementation-specific ----------

class Erased(object):
    def __init__(self, x, identity):
        self._x = x
        self._identity = identity
    def __repr__(self):
        return "Erased(%r, %r)" % (self._x, self._identity)

class Entry(ExtRegistryEntry):
    _about_ = erase_int

    def compute_result_annotation(self, s_obj):
        config = self.bookkeeper.annotator.translator.config
        assert config.translation.taggedpointers, "need to enable tagged pointers to use erase_int"
        assert annmodel.SomeInteger().contains(s_obj)
        return SomeErased()

    def specialize_call(self, hop):
        return hop.r_result.rtype_erase_int(hop)

class Entry(ExtRegistryEntry):
    _about_ = unerase_int

    def compute_result_annotation(self, s_obj):
        assert SomeErased().contains(s_obj)
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        [v] = hop.inputargs(hop.args_r[0])
        assert isinstance(hop.s_result, annmodel.SomeInteger)
        return hop.args_r[0].rtype_unerase_int(hop, v)

def ll_unerase_int(gcref):
    from pypy.rpython.lltypesystem.lloperation import llop
    from pypy.rlib.debug import ll_assert
    x = llop.cast_ptr_to_int(lltype.Signed, gcref)
    ll_assert((x&1) != 0, "unerased_int(): not an integer")
    return x >> 1


class Entry(ExtRegistryEntry):
    _type_ = Erased

    def compute_annotation(self):
        identity = self.instance._identity
        s_obj = self.bookkeeper.immutablevalue(self.instance._x)
        identity.enter_tunnel(self.bookkeeper, s_obj)
        return SomeErased()

# annotation and rtyping support

class SomeErased(annmodel.SomeObject):

    def can_be_none(self):
        return False # cannot be None, but can contain a None

    def rtyper_makerepr(self, rtyper):
        if rtyper.type_system.name == 'lltypesystem':
            return ErasedRepr(rtyper)
        elif rtyper.type_system.name == 'ootypesystem':
            return OOErasedRepr(rtyper)

    def rtyper_makekey(self):
        return self.__class__,

class __extend__(pairtype(SomeErased, SomeErased)):

    def union((serased1, serased2)):
        return SomeErased()


class ErasedRepr(Repr):
    lowleveltype = llmemory.GCREF
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def rtype_erase(self, hop, s_obj):
        hop.exception_cannot_occur()
        r_obj = self.rtyper.getrepr(s_obj)
        if r_obj.lowleveltype is lltype.Void:
            return hop.inputconst(self.lowleveltype,
                                  lltype.nullptr(self.lowleveltype.TO))
        [v_obj] = hop.inputargs(r_obj)
        return hop.genop('cast_opaque_ptr', [v_obj],
                         resulttype=self.lowleveltype)

    def rtype_unerase(self, hop, s_obj):
        [v] = hop.inputargs(hop.args_r[0])
        return hop.genop('cast_opaque_ptr', [v], resulttype=hop.r_result)

    def rtype_unerase_int(self, hop, v):
        return hop.gendirectcall(ll_unerase_int, v)

    def rtype_erase_int(self, hop):
        [v_value] = hop.inputargs(lltype.Signed)
        c_one = hop.inputconst(lltype.Signed, 1)
        hop.exception_is_here()
        v2 = hop.genop('int_add_ovf', [v_value, v_value],
                       resulttype = lltype.Signed)
        v2p1 = hop.genop('int_add', [v2, c_one],
                         resulttype = lltype.Signed)
        v_instance = hop.genop('cast_int_to_ptr', [v2p1],
                               resulttype=self.lowleveltype)
        return v_instance

    def convert_const(self, value):
        if value._identity is _identity_for_ints:
            config = self.rtyper.annotator.translator.config
            assert config.translation.taggedpointers, "need to enable tagged pointers to use erase_int"
            return lltype.cast_int_to_ptr(self.lowleveltype, value._x * 2 + 1)
        bk = self.rtyper.annotator.bookkeeper
        s_obj = value._identity.get_input_annotation(bk)
        r_obj = self.rtyper.getrepr(s_obj)
        if r_obj.lowleveltype is lltype.Void:
            return lltype.nullptr(self.lowleveltype.TO)
        v = r_obj.convert_const(value._x)
        return lltype.cast_opaque_ptr(self.lowleveltype, v)

from pypy.rpython.ootypesystem import ootype

class OOErasedRepr(Repr):
    lowleveltype = ootype.Object
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def rtype_erase(self, hop, s_obj):
        hop.exception_cannot_occur()
        r_obj = self.rtyper.getrepr(s_obj)
        if r_obj.lowleveltype is lltype.Void:
            return hop.inputconst(self.lowleveltype,
                                  ootype.NULL)
        [v_obj] = hop.inputargs(r_obj)
        return hop.genop('cast_to_object', [v_obj],
                         resulttype=self.lowleveltype)

    def rtype_unerase(self, hop, s_obj):
        [v] = hop.inputargs(hop.args_r[0])
        return hop.genop('cast_from_object', [v], resulttype=hop.r_result)

    def rtype_unerase_int(self, hop, v):
        c_one = hop.inputconst(lltype.Signed, 1)
        v2 = hop.genop('oounbox_int', [v], resulttype=hop.r_result)
        return hop.genop('int_rshift', [v2, c_one], resulttype=lltype.Signed)

    def rtype_erase_int(self, hop):
        [v_value] = hop.inputargs(lltype.Signed)
        c_one = hop.inputconst(lltype.Signed, 1)
        hop.exception_is_here()
        v2 = hop.genop('int_add_ovf', [v_value, v_value],
                       resulttype = lltype.Signed)
        v2p1 = hop.genop('int_add', [v2, c_one],
                         resulttype = lltype.Signed)
        return hop.genop('oobox_int', [v2p1], resulttype=hop.r_result)

    def convert_const(self, value):
        if value._identity is _identity_for_ints:
            return value._x # FIXME: what should we do here?
        bk = self.rtyper.annotator.bookkeeper
        s_obj = value._identity.get_input_annotation(bk)
        r_obj = self.rtyper.getrepr(s_obj)
        if r_obj.lowleveltype is lltype.Void:
            return ootype.NULL
        v = r_obj.convert_const(value._x)
        return ootype.cast_to_object(v)
