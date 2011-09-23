from pypy.annotation import model as annmodel
from pypy.tool.pairtype import pairtype
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rclass import getinstancerepr
from pypy.rpython.rmodel import Repr
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem.rclass import OBJECTPTR
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.error import TyperError

from pypy.rpython.ootypesystem import ootype


class SomeVRef(annmodel.SomeObject):

    def __init__(self, s_instance=annmodel.s_None):
        assert (isinstance(s_instance, annmodel.SomeInstance) or
                annmodel.s_None.contains(s_instance))
        self.s_instance = s_instance

    def can_be_none(self):
        return False    # but it can contain s_None, which is only accessible
                        # via simple_call() anyway

    def simple_call(self):
        return self.s_instance

    def rtyper_makerepr(self, rtyper):
        if rtyper.type_system.name == 'lltypesystem':
            return vrefrepr
        elif rtyper.type_system.name == 'ootypesystem':
            return oovrefrepr

    def rtyper_makekey(self):
        return self.__class__,

class __extend__(pairtype(SomeVRef, SomeVRef)):

    def union((vref1, vref2)):
        return SomeVRef(annmodel.unionof(vref1.s_instance, vref2.s_instance))


class VRefRepr(Repr):
    lowleveltype = OBJECTPTR

    def specialize_call(self, hop):
        r_generic_object = getinstancerepr(hop.rtyper, None)
        [v] = hop.inputargs(r_generic_object)   # might generate a cast_pointer
        hop.exception_cannot_occur()
        return v

    def rtype_simple_call(self, hop):
        [v] = hop.inputargs(self)
        hop.exception_is_here()
        v = hop.genop('jit_force_virtual', [v], resulttype = OBJECTPTR)
        return hop.genop('cast_pointer', [v], resulttype = hop.r_result)

    def convert_const(self, value):
        if value() is not None:
            raise TyperError("only supports virtual_ref_None as a"
                             " prebuilt virtual_ref")
        return lltype.nullptr(OBJECTPTR.TO)

from pypy.rpython.ootypesystem.rclass import OBJECT

class OOVRefRepr(VRefRepr):
    lowleveltype = OBJECT
    def rtype_simple_call(self, hop):
        [v] = hop.inputargs(self)
        hop.exception_is_here()
        v = hop.genop('jit_force_virtual', [v], resulttype = OBJECT)
        return hop.genop('oodowncast', [v], resulttype = hop.r_result)
    
    def convert_const(self, value):
        if value() is not None:
            raise TypeError("only supports virtual_ref_None as a"
                            " prebuilt virtual_ref")
        return ootype.ROOT._null

vrefrepr = VRefRepr()
oovrefrepr = OOVRefRepr()
