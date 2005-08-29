from pypy.rpython.lltype import LowLevelType, ContainerType, Struct, GcStruct
from pypy.rpython.lltype import Array, GcArray, FuncType, OpaqueType
from pypy.rpython.lltype import RuntimeTypeInfo, PyObjectType, PyObject
from pypy.rpython.lltype import GC_CONTAINER
from pypy.rpython.lltype import Signed, Unsigned, Float, Char, Bool, Void
from pypy.rpython.lltype import UniChar, Ptr, typeOf, InvalidCast

from pypy.rpython.memory.lltypesimulation import cast_pointer, free
from pypy.rpython.memory.lltypesimulation import simulatorptr as _ptr
from pypy.rpython.memory.lltypesimulation import malloc, functionptr, nullptr
from pypy.rpython.memory.lltypesimulation import pyobjectptr, cast_ptr_to_int
from pypy.rpython.memory.convertlltype import FlowGraphConstantConverter


def notimplemented(*args, **kwargs):
    raise NotImplemented

# the following names might have to be imported from lltype as well
# ForwardReference, GcForwardReference, castable, parentlink

ForwardReference = GcForwardReference = castable = parentlink = notimplemented


# the following names from lltype will probably have to be implemented yet:
# opaqueptr, attachRuntimeTypeInfo, getRuntimeTypeInfo,
# runtime_type_info

opaqueptr = attachRuntimeTypeInfo = notimplemented
getRuntimeTypeInfo = runtime_type_info = notimplemented

del notimplemented

def create_no_gc(llinterp, flowgraphs):
    fgcc = FlowGraphConstantConverter(flowgraphs)
    fgcc.convert()    
    return None

from pypy.rpython.memory.gc import MarkSweepGC, SemiSpaceGC
use_gc = MarkSweepGC
def create_mark_sweep_gc(llinterp, flowgraphs):
    from pypy.rpython.memory.gcwrapper import GcWrapper, QueryTypes
    # XXX there might me GCs that have headers that depend on the type
    # therefore we have to change the query functions to annotatable ones later
    qt = QueryTypes(llinterp)
    gc = use_gc(4096, None, *qt.get_setup_query_functions())
    fgcc = FlowGraphConstantConverter(flowgraphs, gc, qt)
    fgcc.convert()
    gc.set_query_functions(*qt.create_query_functions())
    wrapper = GcWrapper(llinterp, gc, qt, fgcc.cvter.constantroots)
    return wrapper

prepare_graphs_and_create_gc = create_no_gc
