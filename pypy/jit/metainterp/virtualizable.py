
from pypy.jit.metainterp import history
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import llhelper, cast_base_ptr_to_instance
from pypy.annotation.model import lltype_to_annotation
from pypy.rlib.objectmodel import we_are_translated

class VirtualizableDesc(history.AbstractValue):
    hash = 0

    def __init__(self, cpu, TOPSTRUCT, STRUCTTYPE):
        "NOT_RPYTHON"
        self.virtuals     = [cpu.fielddescrof(STRUCTTYPE, 'inst_' + name) for
                             name in TOPSTRUCT._hints['virtuals']]
