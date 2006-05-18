from pypy.rpython.memory.convertlltype import FlowGraphConstantConverter
from pypy.rpython.memory.lltypesimulation import free
from pypy.rpython.memory.lltypesimulation import simulatorptr as _ptr
from pypy.rpython.memory.lltypesimulation import malloc, functionptr, nullptr
from pypy.rpython.memory.lltypesimulation import pyobjectptr
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, raw_memcopy

def raw_malloc_usage(sz):
    return sz

def notimplemented(*args, **kwargs):
    raise NotImplemented

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
def create_gc(llinterp, flowgraphs):
    import py; py.test.skip("out-of-progress")
    from pypy.rpython.memory.gcwrapper import GcWrapper, AnnotatingGcWrapper
    wrapper = GcWrapper(llinterp, flowgraphs, use_gc)
    return wrapper
    
def create_gc_run_on_llinterp(llinterp, flowgraphs):
    from pypy.rpython.memory.gcwrapper import GcWrapper, AnnotatingGcWrapper
    wrapper = AnnotatingGcWrapper(llinterp, flowgraphs, use_gc)
    return wrapper


prepare_graphs_and_create_gc = create_no_gc
