""" Contains a mechanism for turning any class instance and any integer into a
pointer-like thing. Gives full control over pointer tagging, i.e. there won't
be tag checks everywhere in the C code. """

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



def erase(x):
    """Creates an 'erased' object that contains a reference to 'x'. Nothing can
    be done with this object, except calling unerase(y, <type>) on it.
    x needs to be either an instance or an integer fitting into 31/63 bits."""
    if isinstance(x, int):
        res = 2 * x + 1
        if res > sys.maxint or res < -sys.maxint - 1:
            raise OverflowError
    assert not isinstance(x, list)
    return Erased(x)

def erase_fixedsizelist(l, type):
    assert isinstance(l, list)
    result = Erased(l)
    result._list_item_type = type
    return result

def unerase(y, type):
    """Turn an erased object back into an object of type 'type'."""
    if y._x is None:
        return None
    assert isinstance(y._x, type)
    return y._x

def unerase_fixedsizelist(y, type):
    if y._x is None:
        return None
    assert isinstance(y._x, list)
    if y._x:
        assert isinstance(y._x[0], type)
    return y._x

def is_integer(e):
    """Gives information whether the erased argument is a tagged integer or not."""
    return isinstance(e._x, int)


# ---------- implementation-specific ----------

class Erased(object):
    _list_item_type = None
    def __init__(self, x):
        self._x = x
    def __repr__(self):
        return "Erased(%r)" % (self._x, )

class Entry(ExtRegistryEntry):
    _about_ = erase

    def compute_result_annotation(self, s_obj):
        return SomeErased()

    def specialize_call(self, hop):
        return hop.r_result.specialize_call(hop)

class Entry(ExtRegistryEntry):
    _about_ = erase_fixedsizelist

    def compute_result_annotation(self, s_arg, s_type):
        # s_type ignored: only for prebuilt erased lists
        assert isinstance(s_arg, annmodel.SomeList)
        s_arg.listdef.never_resize()
        return SomeErased()

    def specialize_call(self, hop):
        return hop.r_result.specialize_call(hop)

class Entry(ExtRegistryEntry):
    _about_ = unerase

    def compute_result_annotation(self, s_obj, s_type):
        assert s_type.is_constant()
        if s_type.const is int:
            return annmodel.SomeInteger()
        assert isinstance(s_type, annmodel.SomePBC)
        assert len(s_type.descriptions) == 1
        clsdef = s_type.descriptions.keys()[0].getuniqueclassdef()
        return annmodel.SomeInstance(clsdef)

    def specialize_call(self, hop):
        v, t = hop.inputargs(hop.args_r[0], lltype.Void)
        if isinstance(hop.s_result, annmodel.SomeInteger):
            c_one = hop.inputconst(lltype.Signed, 1)
            vi = hop.genop('cast_ptr_to_int', [v], resulttype=lltype.Signed)
            return hop.genop('int_rshift', [vi, c_one], resulttype=lltype.Signed)
        return hop.genop('cast_opaque_ptr', [v], resulttype = hop.r_result)

class Entry(ExtRegistryEntry):
    _about_ = unerase_fixedsizelist

    def compute_result_annotation(self, s_obj, s_type):
        assert isinstance(s_type, annmodel.SomePBC)
        assert len(s_type.descriptions) == 1
        clsdef = s_type.descriptions.keys()[0].getuniqueclassdef()
        s_item = annmodel.SomeInstance(clsdef)
        return self.bookkeeper.newlist(s_item)

    def specialize_call(self, hop):
        v, t = hop.inputargs(hop.args_r[0], lltype.Void)
        return hop.genop('cast_opaque_ptr', [v], resulttype = hop.r_result)


class Entry(ExtRegistryEntry):
    _about_ = is_integer

    def compute_result_annotation(self, s_obj):
        return annmodel.SomeBool()

    def specialize_call(self, hop):
        v, = hop.inputargs(hop.args_r[0])
        c_one = hop.inputconst(lltype.Signed, 1)
        vi = hop.genop('cast_ptr_to_int', [v], resulttype=lltype.Signed)
        vb = hop.genop('int_and', [vi, c_one], resulttype=lltype.Signed)
        return hop.genop('int_is_true', [vb], resulttype=lltype.Bool)


class Entry(ExtRegistryEntry):
    _type_ = Erased

    def compute_annotation(self):
        s_obj = self.bookkeeper.immutablevalue(self.instance._x)
        if self.instance._list_item_type is not None:
            # only non-resizable lists of instances for now
            clsdef = self.bookkeeper.getuniqueclassdef(self.instance._list_item_type)
            s_item = annmodel.SomeInstance(clsdef)
            s_obj.listdef.generalize(s_item)
            self.instance._s_list = s_obj
        return SomeErased()

# annotation and rtyping support

class SomeErased(annmodel.SomeObject):

    def __init__(self, s_obj=None):
        self.s_obj = s_obj # only non-None for constants

    def can_be_none(self):
        return False # cannot be None, but can contain a None

    def rtyper_makerepr(self, rtyper):
        return ErasedRepr(rtyper)

    def rtyper_makekey(self):
        return self.__class__,

class __extend__(pairtype(SomeErased, SomeErased)):

    def union((serased1, serased2)):
        return SomeErased()


class ErasedRepr(Repr):
    lowleveltype = llmemory.GCREF
    def __init__(self, rtyper):
        self.rtyper = rtyper

    def specialize_call(self, hop):
        s_arg = hop.args_s[0]
        r_generic_object = getinstancerepr(hop.rtyper, None)
        if (isinstance(s_arg, annmodel.SomeInstance) or
                (s_arg.is_constant() and s_arg.const is None)):
            hop.exception_cannot_occur()
            [v_instance] = hop.inputargs(r_generic_object)   # might generate a cast_pointer
            v = hop.genop('cast_opaque_ptr', [v_instance],
                          resulttype=self.lowleveltype)
            return v
        elif isinstance(s_arg, annmodel.SomeList):
            hop.exception_cannot_occur()
            r_list = self.rtyper.getrepr(s_arg)
            v_list = hop.inputarg(r_list, 0)
            v = hop.genop('cast_opaque_ptr', [v_list],
                          resulttype=self.lowleveltype)
            return v
        else:
            assert isinstance(s_arg, annmodel.SomeInteger)
            v_value = hop.inputarg(lltype.Signed, arg=0)
            c_one = hop.inputconst(lltype.Signed, 1)
            hop.exception_is_here()
            v2 = hop.genop('int_lshift_ovf', [v_value, c_one],
                           resulttype = lltype.Signed)
            v2p1 = hop.genop('int_add', [v2, c_one],
                             resulttype = lltype.Signed)
            v_instance = hop.genop('cast_int_to_ptr', [v2p1],
                                   resulttype=self.lowleveltype)
            v = hop.genop('cast_opaque_ptr', [v_instance],
                          resulttype=self.lowleveltype)
            return v


    def convert_const(self, value):
        if isinstance(value._x, int):
            return lltype.cast_int_to_ptr(self.lowleveltype, value._x * 2 + 1)
        if isinstance(value._x, list):
            r_list = self.rtyper.getrepr(value._s_list)
            v = r_list.convert_const(value._x)
            return lltype.cast_opaque_ptr(self.lowleveltype, v)
        else:
            r_generic_object = getinstancerepr(self.rtyper, None)
            v = r_generic_object.convert_const(value._x)
            return lltype.cast_opaque_ptr(self.lowleveltype, v)

