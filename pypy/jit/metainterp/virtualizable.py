
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
        self.fields = self.catch_all_fields(cpu, STRUCTTYPE)

    def catch_all_fields(self, cpu, S):
        lst = []
        p = S
        while True:
            lst.extend(p._names)
            if getattr(p, 'super', None) is not None:
                p = p.super
            else:
                break
        return [cpu.fielddescrof(S, name) for name in lst if
                name.startswith('inst_') and hasattr(S, name)]

