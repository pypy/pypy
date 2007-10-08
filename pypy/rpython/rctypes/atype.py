"""
Var-sized arrays, i.e. arrays whose size is not known at annotation-time.
"""

from pypy.annotation.model import SomeCTypesObject
from pypy.annotation.model import SomeBuiltin, SomeInteger, SomeString
from pypy.tool.pairtype import pair, pairtype
from pypy.rpython.extregistry import ExtRegistryEntry


class SomeCTypesType(SomeBuiltin):
    """A ctypes type behaves like a built-in function, because it can only
    be called -- with the exception of 'ctype*int' to build array types.
    """
    def rtyper_makerepr(self, rtyper):
        from pypy.rpython.rctypes.rtype import TypeRepr
        return TypeRepr(self)

    def rtyper_makekey(self):
        return SomeCTypesType, getattr(self, 'const', None)


class SomeVarSizedCTypesType(SomeBuiltin):
    """A ctypes built at runtime as 'ctype*int'.
    Note that at the moment 'ctype*int*int' is not supported.
    """
    def __init__(self, ctype_item):
        from pypy.rpython.rctypes.aarray import VarSizedArrayType
        ctype_array = VarSizedArrayType(ctype_item)
        SomeBuiltin.__init__(self, ctype_array.get_instance_annotation)
        self.ctype_array = ctype_array

    def rtyper_makerepr(self, rtyper):
        assert self.s_self is None
        from pypy.rpython.rctypes.rtype import VarSizedTypeRepr
        return VarSizedTypeRepr()

    def rtyper_makekey(self):
        return SomeVarSizedCTypesType, self.ctype_array


class __extend__(pairtype(SomeCTypesType, SomeInteger)):
    def mul((s_ctt, s_int)):
        entry = s_ctt.analyser.im_self   # fish fish
        ctype_item  = entry.instance
        return SomeVarSizedCTypesType(ctype_item)
    mul.can_only_throw = []
