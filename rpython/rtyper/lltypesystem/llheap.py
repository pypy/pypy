# only for the LLInterpreter.  Don't use directly.

from rpython.rtyper.lltypesystem.lltype import malloc, free, typeOf
from rpython.rtyper.lltypesystem.llmemory import weakref_create, weakref_deref

setfield = setattr
from operator import setitem as setarrayitem
from rpython.rlib.rgc import can_move, collect, add_memory_pressure

def setinterior(toplevelcontainer, inneraddr, INNERTYPE, newvalue,
                offsets=None):
    assert typeOf(newvalue) == INNERTYPE
    # xxx access the address object's ref() directly for performance
    inneraddr.ref()[0] = newvalue

from rpython.rtyper.lltypesystem.lltype import cast_ptr_to_int as gc_id

def weakref_create_getlazy(objgetter):
    return weakref_create(objgetter())

malloc_nonmovable = malloc

def shrink_array(p, smallersize):
    return False


def thread_run():
    pass

def thread_start():
    pass

def thread_die():
    pass
