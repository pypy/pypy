# Base classes describing annotation and rtyping
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython import extregistry
from pypy.rpython.extregistry import ExtRegistryEntry


class CTypesCallEntry(ExtRegistryEntry):
    "Annotation and rtyping of calls to ctypes types."

    def compute_result_annotation(self, *args_s, **kwds_s):
        ctype = self.instance    # the ctype is the called object
        return SomeCTypesObject(ctype, SomeCTypesObject.OWNSMEMORY)


class CTypesObjEntry(ExtRegistryEntry):
    "Annotation and rtyping of ctypes instances."

    def compute_annotation(self):
        ctype = self.type
        return SomeCTypesObject(ctype, SomeCTypesObject.OWNSMEMORY)


# Importing for side effect of registering types with extregistry
import pypy.rpython.rctypes.aprimitive
import pypy.rpython.rctypes.apointer
import pypy.rpython.rctypes.aarray
import pypy.rpython.rctypes.afunc
import pypy.rpython.rctypes.achar_p
import pypy.rpython.rctypes.astruct
import pypy.rpython.rctypes.avoid_p
import pypy.rpython.rctypes.astringbuf
import pypy.rpython.rctypes.apyobject


# Register the correspondance between SomeCTypesObject and the get_repr()
# functions attached to the extregistry to create CTypesReprs

class __extend__( SomeCTypesObject ):
    def rtyper_makerepr( self, rtyper ):
        entry = extregistry.lookup_type(self.knowntype)
        return entry.get_repr(rtyper, self)

    def rtyper_makekey( self ):
        return self.__class__, self.knowntype, self.memorystate
