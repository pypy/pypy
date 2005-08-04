# XXX this whole thing is messy.

# choose the lltype implementation with the following variable:
# 0 is the original pypy/rpython/lltype.py
# 1 is the lltype implementation on top of the memory simulator:
#     pypy/rpython/memory/lltypesimulation.py

use_lltype_number = 0

def raising(*args):
    raise NotImplemented, "missing function"

if use_lltype_number == 0:
    from pypy.rpython.lltype import _ptr, Ptr, Void, typeOf, malloc, cast_pointer, PyObject, pyobjectptr
    from pypy.rpython.lltype import Array, Struct
    from pypy.rpython.rmodel import getfunctionptr
elif use_lltype_number == 1:
    from pypy.rpython.lltype import Ptr, Void, typeOf, PyObject
    from pypy.rpython.lltype import Array, Struct
    from pypy.rpython.memory.lltypesimulation import simulatorptr as _ptr, cast_pointer, malloc
    pyobjectptr = raising
    getfunctionptr = raising
else:
    raise ValueError, "unknown lltype number"
