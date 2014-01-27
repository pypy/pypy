"""
Code for annotating low-level thingies.
"""
from rpython.annotator.model import SomeObject
from rpython.rtyper.lltypesystem import lltype

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
