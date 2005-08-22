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
    from pypy.rpython.memory.gcwrapper import GcWrapper, LLInterpObjectModel
    #XXX hackish: we need the gc before the object model is ready
    gc = use_gc(None, 4096)
    fgcc = FlowGraphConstantConverter(flowgraphs, gc)
    fgcc.convert()    
    om = LLInterpObjectModel(llinterp, fgcc.cvter.types,
                             fgcc.cvter.type_to_typeid,
                             fgcc.cvter.constantroots)
    gc.objectmodel = om
    wrapper = GcWrapper(llinterp, gc)
    return wrapper

prepare_graphs_and_create_gc = create_mark_sweep_gc
