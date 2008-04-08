# only for the LLInterpreter.  Don't use directly.

from pypy.rpython.lltypesystem.lltype import pyobjectptr, malloc, free, typeOf
from pypy.rpython.lltypesystem.llmemory import weakref_create, weakref_deref

setfield = setattr
from operator import setitem as setarrayitem
from pypy.rlib.rgc import collect, disable_finalizers, enable_finalizers

def setinterior(toplevelcontainer, inneraddr, INNERTYPE, newvalue):
    assert typeOf(newvalue) == INNERTYPE
    # xxx access the address object's ref() directly for performance
    inneraddr.ref()[0] = newvalue

from pypy.rpython.lltypesystem.lltype import cast_ptr_to_int as gc_id

def weakref_create_getlazy(objgetter):
    return weakref_create(objgetter())

def coalloc(T, coallocator, n=None, zero=True):
    # ignore the coallocator
    return malloc(T, n, zero=zero)
