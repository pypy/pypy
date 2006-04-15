# Importing for side effect of registering types with extregistry
import pypy.rpython.rctypes.rprimitive
import pypy.rpython.rctypes.rpointer
import pypy.rpython.rctypes.rarray
import pypy.rpython.rctypes.rfunc
import pypy.rpython.rctypes.rchar_p
import pypy.rpython.rctypes.rstruct
import pypy.rpython.rctypes.rvoid_p


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
