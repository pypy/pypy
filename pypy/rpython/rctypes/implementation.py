# Importing for side effect of registering types with extregistry
import pypy.rpython.rctypes.aprimitive
import pypy.rpython.rctypes.apointer
import pypy.rpython.rctypes.aarray
import pypy.rpython.rctypes.afunc
import pypy.rpython.rctypes.achar_p
import pypy.rpython.rctypes.astruct
import pypy.rpython.rctypes.avoid_p
import pypy.rpython.rctypes.astringbuf


# Register the correspondance between SomeCTypesObject and the get_repr()
# functions attached to the extregistry to create CTypesReprs

from pypy.annotation.model import SomeCTypesObject
from pypy.rpython import extregistry

class __extend__( SomeCTypesObject ):
    def rtyper_makerepr( self, rtyper ):
        entry = extregistry.lookup_type(self.knowntype)
        return entry.get_repr(rtyper, self)

    def rtyper_makekey( self ):
        return self.__class__, self.knowntype, self.memorystate
