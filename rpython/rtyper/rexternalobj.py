from rpython.annotator import model as annmodel
from rpython.rtyper import extregistry
from rpython.rtyper.lltypesystem import lltype

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
