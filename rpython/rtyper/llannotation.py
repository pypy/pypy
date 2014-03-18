"""
Code for annotating low-level thingies.
"""
from types import MethodType
from rpython.tool.pairtype import pair, pairtype
from rpython.annotator.model import (
    SomeObject, SomeSingleFloat, SomeFloat, SomeLongFloat, SomeChar,
    SomeUnicodeCodePoint, SomeInteger, SomeString, SomeImpossibleValue,
    s_None, s_Bool, UnionError, AnnotatorError, SomeBool)
from rpython.rtyper.lltypesystem import lltype, llmemory

class SomeAddress(SomeObject):
    immutable = True

    def can_be_none(self):
        return False

    def is_null_address(self):
        return self.is_immutable_constant() and not self.const

    def getattr(self, s_attr):
        assert s_attr.is_constant()
        assert isinstance(s_attr, SomeString)
        assert s_attr.const in llmemory.supported_access_types
        return SomeTypedAddressAccess(
            llmemory.supported_access_types[s_attr.const])
    getattr.can_only_throw = []

    def bool(self):
        return s_Bool

class SomeTypedAddressAccess(SomeObject):
    """This class is used to annotate the intermediate value that
    appears in expressions of the form:
    addr.signed[offset] and addr.signed[offset] = value
    """

    def __init__(self, type):
        self.type = type

    def can_be_none(self):
        return False


class __extend__(pairtype(SomeAddress, SomeAddress)):
    def union((s_addr1, s_addr2)):
        return SomeAddress()

    def sub((s_addr1, s_addr2)):
        from rpython.annotator.bookkeeper import getbookkeeper
        if s_addr1.is_null_address() and s_addr2.is_null_address():
            return getbookkeeper().immutablevalue(0)
        return SomeInteger()

    def is_((s_addr1, s_addr2)):
        assert False, "comparisons with is not supported by addresses"

class __extend__(pairtype(SomeTypedAddressAccess, SomeTypedAddressAccess)):
    def union((s_taa1, s_taa2)):
        assert s_taa1.type == s_taa2.type
        return s_taa1

class __extend__(pairtype(SomeTypedAddressAccess, SomeInteger)):
    def getitem((s_taa, s_int)):
        return lltype_to_annotation(s_taa.type)
    getitem.can_only_throw = []

    def setitem((s_taa, s_int), s_value):
        assert annotation_to_lltype(s_value) is s_taa.type
    setitem.can_only_throw = []


class __extend__(pairtype(SomeAddress, SomeInteger)):
    def add((s_addr, s_int)):
        return SomeAddress()

    def sub((s_addr, s_int)):
        return SomeAddress()

class __extend__(pairtype(SomeAddress, SomeImpossibleValue)):
    # need to override this specifically to hide the 'raise UnionError'
    # of pairtype(SomeAddress, SomeObject).
    def union((s_addr, s_imp)):
        return s_addr

class __extend__(pairtype(SomeImpossibleValue, SomeAddress)):
    # need to override this specifically to hide the 'raise UnionError'
    # of pairtype(SomeObject, SomeAddress).
    def union((s_imp, s_addr)):
        return s_addr

class __extend__(pairtype(SomeAddress, SomeObject)):
    def union((s_addr, s_obj)):
        raise UnionError(s_addr, s_obj)

class __extend__(pairtype(SomeObject, SomeAddress)):
    def union((s_obj, s_addr)):
        raise UnionError(s_obj, s_addr)


class SomePtr(SomeObject):
    knowntype = lltype._ptr
    immutable = True

    def __init__(self, ll_ptrtype):
        assert isinstance(ll_ptrtype, lltype.Ptr)
        self.ll_ptrtype = ll_ptrtype

    def can_be_none(self):
        return False

    def getattr(self, s_attr):
        from rpython.annotator.bookkeeper import getbookkeeper
        if not s_attr.is_constant():
            raise AnnotatorError("getattr on ptr %r with non-constant "
                                 "field-name" % self.ll_ptrtype)
        example = self.ll_ptrtype._example()
        try:
            v = example._lookup_adtmeth(s_attr.const)
        except AttributeError:
            v = getattr(example, s_attr.const)
            return ll_to_annotation(v)
        else:
            if isinstance(v, MethodType):
                ll_ptrtype = lltype.typeOf(v.im_self)
                assert isinstance(ll_ptrtype, (lltype.Ptr, lltype.InteriorPtr))
                return SomeLLADTMeth(ll_ptrtype, v.im_func)
            return getbookkeeper().immutablevalue(v)
    getattr.can_only_throw = []

    def len(self):
        from rpython.annotator.bookkeeper import getbookkeeper
        length = self.ll_ptrtype._example()._fixedlength()
        if length is None:
            return SomeObject.len(self)
        else:
            return getbookkeeper().immutablevalue(length)

    def setattr(self, s_attr, s_value): # just doing checking
        if not s_attr.is_constant():
            raise AnnotatorError("setattr on ptr %r with non-constant "
                                 "field-name" % self.ll_ptrtype)
        example = self.ll_ptrtype._example()
        if getattr(example, s_attr.const) is not None:  # ignore Void s_value
            v_lltype = annotation_to_lltype(s_value)
            setattr(example, s_attr.const, v_lltype._defl())

    def call(self, args):
        args_s, kwds_s = args.unpack()
        if kwds_s:
            raise Exception("keyword arguments to call to a low-level fn ptr")
        info = 'argument to ll function pointer call'
        llargs = [annotation_to_lltype(s_arg, info)._defl() for s_arg in args_s]
        v = self.ll_ptrtype._example()(*llargs)
        return ll_to_annotation(v)

    def bool(self):
        result = SomeBool()
        if self.is_constant():
            result.const = bool(self.const)
        return result


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

    def call(self, args):
        from rpython.annotator.bookkeeper import getbookkeeper
        bookkeeper = getbookkeeper()
        s_func = bookkeeper.immutablevalue(self.func)
        return s_func.call(args.prepend(lltype_to_annotation(self.ll_ptrtype)))


class __extend__(pairtype(SomePtr, SomePtr)):
    def union((p1, p2)):
        if p1.ll_ptrtype != p2.ll_ptrtype:
            raise UnionError(p1, p2)
        return SomePtr(p1.ll_ptrtype)

class __extend__(pairtype(SomePtr, SomeInteger)):

    def getitem((p, int1)):
        example = p.ll_ptrtype._example()
        try:
            v = example[0]
        except IndexError:
            return None       # impossible value, e.g. FixedSizeArray(0)
        return ll_to_annotation(v)
    getitem.can_only_throw = []

    def setitem((p, int1), s_value):   # just doing checking
        example = p.ll_ptrtype._example()
        if example[0] is not None:  # ignore Void s_value
            v_lltype = annotation_to_lltype(s_value)
            example[0] = v_lltype._defl()
    setitem.can_only_throw = []

class __extend__(pairtype(SomePtr, SomeObject)):
    def union((p, obj)):
        raise UnionError(p, obj)

    def getitem((p, obj)):
        raise AnnotatorError("ptr %r getitem index not an int: %r" %
                             (p.ll_ptrtype, obj))

    def setitem((p, obj), s_value):
        raise AnnotatorError("ptr %r setitem index not an int: %r" %
                             (p.ll_ptrtype, obj))

class __extend__(pairtype(SomeObject, SomePtr)):
    def union((obj, p2)):
        return pair(p2, obj).union()


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
