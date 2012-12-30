from rpython.annotator import model as annmodel
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.ootypesystem import ootype
from rpython.rtyper.rmodel import Repr
from rpython.rtyper import rbuiltin
from rpython.flowspace.model import Constant, Variable
from rpython.rtyper import extregistry
from rpython.annotator.signature import annotation
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

