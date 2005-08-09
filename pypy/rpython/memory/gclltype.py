from pypy.rpython.lltype import LowLevelType, ContainerType, Struct, GcStruct
from pypy.rpython.lltype import Array, GcArray, FuncType, OpaqueType
from pypy.rpython.lltype import RuntimeTypeInfo, PyObjectType, PyObject
from pypy.rpython.lltype import GC_CONTAINER
from pypy.rpython.lltype import Signed, Unsigned, Float, Char, Bool, Void
from pypy.rpython.lltype import UniChar, Ptr, typeOf, InvalidCast

from pypy.rpython.memory.lltypesimulation import cast_pointer
from pypy.rpython.memory.lltypesimulation import simulatorptr as _ptr
from pypy.rpython.memory.lltypesimulation import malloc, functionptr, nullptr
from pypy.rpython.memory.lltypesimulation import pyobjectptr


def notimplemented(*args, **kwargs):
    raise NotImplemented

# the following names might have to be imported from lltype as well
# ForwardReference, GcForwardReference, castable, parentlink

ForwardReference = GcForwardReference = castable = parentlink = notimplemented


# the following names from lltype will probably have to be implemented yet:
# opaqueptr, pyobjectptr, attachRuntimeTypeInfo, getRuntimeTypeInfo,
# runtime_type_info

opaqueptr = attachRuntimeTypeInfo = notimplemented
getRuntimeTypeInfo = runtime_type_info = notimplemented

del notimplemented

def prepare_graphs(flowgraphs):
    from pypy.rpython.memory.convertlltype import FlowGraphConstantConverter
    fgcc = FlowGraphConstantConverter(flowgraphs)
    fgcc.convert()

