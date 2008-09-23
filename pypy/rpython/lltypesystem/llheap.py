# only for the LLInterpreter.  Don't use directly.

from pypy.rpython.lltypesystem.lltype import pyobjectptr, malloc, free, typeOf
from pypy.rpython.lltypesystem.llmemory import weakref_create, weakref_deref

setfield = setattr
from operator import setitem as setarrayitem
from pypy.rlib.rgc import collect
from pypy.rlib.rgc import can_move

def setinterior(toplevelcontainer, inneraddr, INNERTYPE, newvalue):
    assert typeOf(newvalue) == INNERTYPE
    # xxx access the address object's ref() directly for performance
    inneraddr.ref()[0] = newvalue

from pypy.rpython.lltypesystem.lltype import cast_ptr_to_int as gc_id

def weakref_create_getlazy(objgetter):
    return weakref_create(objgetter())

malloc_nonmovable = malloc

def malloc_resizable_buffer(TP, size):
    return malloc(TP, size)

def resize_buffer(buf, old_size, new_size):
    ll_str = malloc(typeOf(buf).TO, new_size)
    for i in range(old_size):
        ll_str.chars[i] = buf.chars[i]
    return ll_str

def finish_building_buffer(buf, final_size):
    ll_str = malloc(typeOf(buf).TO, final_size)
    for i in range(final_size):
        ll_str.chars[i] = buf.chars[i]
    return ll_str

def thread_prepare():
    pass

def thread_run():
    pass

def thread_die():
    pass
