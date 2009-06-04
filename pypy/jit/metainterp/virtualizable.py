
from pypy.jit.metainterp import history
from pypy.jit.metainterp.typesystem import llhelper, oohelper
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llhelper, cast_base_ptr_to_instance
from pypy.annotation.model import lltype_to_annotation
from pypy.rlib.objectmodel import we_are_translated

class VirtualizableDesc(history.AbstractDescr):
    hash = 0

    def __init__(self, cpu, TOPSTRUCT, STRUCTTYPE):
        "NOT_RPYTHON"
        if cpu.is_oo:
            prefix = 'o'
        else:
            prefix = 'inst_'
        self.virtuals = [cpu.fielddescrof(STRUCTTYPE, prefix+name)
                         for name in TOPSTRUCT._hints['virtuals']]
        self.fields = self.catch_all_fields(cpu, STRUCTTYPE)

    def catch_all_fields(self, cpu, S):
        if isinstance(S, ootype.OOType):
            return self.catch_all_fields_ootype(cpu, S)
        return self.catch_all_fields_lltype(cpu, S)

    def catch_all_fields_lltype(self, cpu, S):
        lst = []
        p = S
        while True:
            lst.extend(p._names)
            if getattr(p, 'super', None) is not None:
                p = p.super
            else:
                break
        return [cpu.fielddescrof(S, name) for name in lst if
                name.startswith('inst_')]

    def catch_all_fields_ootype(self, cpu, S):
        lst = S._allfields().keys()
        return [cpu.fielddescrof(S, name) for name in lst]
