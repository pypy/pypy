"""
Code for annotating low-level thingies.
"""
from rpython.annotator.model import (
    SomeObject, SomeSingleFloat, SomeFloat, SomeLongFloat, SomeChar,
    SomeUnicodeCodePoint, SomeInteger, s_None, s_Bool)
from rpython.rtyper.lltypesystem import lltype, llmemory

class SomeAddress(SomeObject):
    immutable = True

    def can_be_none(self):
        return False

    def is_null_address(self):
        return self.is_immutable_constant() and not self.const

class SomeTypedAddressAccess(SomeObject):
    """This class is used to annotate the intermediate value that
    appears in expressions of the form:
    addr.signed[offset] and addr.signed[offset] = value
    """

    def __init__(self, type):
        self.type = type

    def can_be_none(self):
        return False

class SomePtr(SomeObject):
    knowntype = lltype._ptr
    immutable = True

    def __init__(self, ll_ptrtype):
        assert isinstance(ll_ptrtype, lltype.Ptr)
        self.ll_ptrtype = ll_ptrtype

    def can_be_none(self):
        return False


class SomeInteriorPtr(SomePtr):
    def __init__(self, ll_ptrtype):
        assert isinstance(ll_ptrtype, lltype.InteriorPtr)
        self.ll_ptrtype = ll_ptrtype


class SomeLLADTMeth(SomeObject):
    immutable = True

    def __init__(self, ll_ptrtype, func):
        self.ll_ptrtype = ll_ptrtype
        self.func = func

    def can_be_none(self):
        return False


annotation_to_ll_map = [
    (SomeSingleFloat(), lltype.SingleFloat),
    (s_None, lltype.Void),   # also matches SomeImpossibleValue()
    (s_Bool, lltype.Bool),
    (SomeFloat(), lltype.Float),
    (SomeLongFloat(), lltype.LongFloat),
    (SomeChar(), lltype.Char),
    (SomeUnicodeCodePoint(), lltype.UniChar),
    (SomeAddress(), llmemory.Address),
]


def annotation_to_lltype(s_val, info=None):
    if isinstance(s_val, SomeInteriorPtr):
        p = s_val.ll_ptrtype
        if 0 in p.offsets:
            assert list(p.offsets).count(0) == 1
            return lltype.Ptr(lltype.Ptr(p.PARENTTYPE)._interior_ptr_type_with_index(p.TO))
        else:
            return lltype.Ptr(p.PARENTTYPE)
    if isinstance(s_val, SomePtr):
        return s_val.ll_ptrtype
    if type(s_val) is SomeInteger:
        return lltype.build_number(None, s_val.knowntype)

    for witness, T in annotation_to_ll_map:
        if witness.contains(s_val):
            return T
    if info is None:
        info = ''
    else:
        info = '%s: ' % info
    raise ValueError("%sshould return a low-level type,\ngot instead %r" % (
        info, s_val))

ll_to_annotation_map = dict([(ll, ann) for ann, ll in annotation_to_ll_map])

def lltype_to_annotation(T):
    try:
        s = ll_to_annotation_map.get(T)
    except TypeError:
        s = None    # unhashable T, e.g. a Ptr(GcForwardReference())
    if s is None:
        if isinstance(T, lltype.Typedef):
            return lltype_to_annotation(T.OF)
        if isinstance(T, lltype.Number):
            return SomeInteger(knowntype=T._type)
        elif isinstance(T, lltype.InteriorPtr):
            return SomeInteriorPtr(T)
        else:
            return SomePtr(T)
    else:
        return s


def ll_to_annotation(v):
    if v is None:
        # i think we can only get here in the case of void-returning
        # functions
        return s_None
    if isinstance(v, lltype._interior_ptr):
        ob = v._parent
        if ob is None:
            raise RuntimeError
        T = lltype.InteriorPtr(lltype.typeOf(ob), v._T, v._offsets)
        return SomeInteriorPtr(T)
    return lltype_to_annotation(lltype.typeOf(v))
