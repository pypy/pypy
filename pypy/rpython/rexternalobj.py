from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rmodel import Repr
from pypy.rpython import rbuiltin
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython import extregistry
from pypy.annotation.signature import annotation
from pypy.tool.pairtype import pairtype

# ExternalObjects

class __extend__(annmodel.SomeExternalObject):

    def rtyper_makerepr(self, rtyper):
       # delegate to the get_repr() of the extregistrered Entry class
        entry = extregistry.lookup_type(self.knowntype)
        return entry.get_repr(rtyper, self)

    def rtyper_makekey(self):
        # grab all attributes of the SomeExternalObject for the key
        attrs = lltype.frozendict(self.__dict__)
        if 'const' in attrs:
            del attrs['const']
        if 'const_box' in attrs:
            del attrs['const_box']
        return self.__class__, attrs

