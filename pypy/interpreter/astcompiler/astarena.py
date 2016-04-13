from rpython.rtyper import rmodel, rclass, rbuiltin
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.flowspace.model import Constant
from rpython.annotator import model as annmodel
from pypy.interpreter.astcompiler import ast
from rpython.rlib.rawstorage import alloc_raw_storage
from rpython.rtyper.annlowlevel import (cast_instance_to_gcref,
                                        cast_gcref_to_instance)

# This is the most important line!
ast.AST._alloc_flavor_ = 'raw'

class Arena(object):
    def __init__(self):
        self.memory_blocks = []
        self.objects = []

    def allocate(self, cls):
        xxx

def _all_subclasses(cls):
    yield cls
    for subclass in cls.__subclasses__():
        for c in _all_subclasses(subclass):
            yield c


class SomeAstInstance(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return _getinstancerepr(rtyper, self.classdef)


class SomeArena(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return ArenaRepr()

ARENA = lltype.GcStruct('Arena',
                        ('storage', llmemory.Address),
                        ('size', lltype.Signed),
                        ('current', lltype.Signed),
                        )

class ArenaRepr(rmodel.Repr):
    lowleveltype = lltype.Ptr(ARENA)

    def rtyper_new(self, hop):
        hop.exception_cannot_occur()
        return hop.gendirectcall(self.ll_new)

    @staticmethod
    def ll_new():
        ll_arena = lltype.malloc(ARENA)
        SIZE = 1000 * 1000
        ll_arena.storage = llmemory.cast_ptr_to_adr(alloc_raw_storage(
            SIZE, track_allocation=False, zero=False))
        ll_arena.size = SIZE
        ll_arena.current = 0
        return ll_arena

    @staticmethod
    def ll_allocate(ll_arena, TYPE):
        size = 100 #  XXX rffi.sizeof(TYPE.TO)
        offset = ll_arena.current
        assert offset + size < ll_arena.size
        ll_arena.current += size
        return rffi.cast(TYPE, ll_arena.storage + offset)

class AstNodeRepr(rclass.InstanceRepr):
    def alloc_instance(self, llops, classcallhop=None, nonmovable=False):
        if classcallhop is None:
            raise TyperError("must instantiate %r by calling the class" % (
                self.classdef,))
        hop = classcallhop
        r_arena = hop.args_r[0]
        v_arena = hop.inputarg(r_arena, 0)
        v_size = hop.inputconst(lltype.Signed, 
                                rffi.sizeof(self.lowleveltype))
        cTYPE = hop.inputconst(lltype.Void, self.lowleveltype)
        v_ptr = hop.llops.gendirectcall(r_arena.ll_allocate, v_arena, cTYPE)
        # return rbuiltin.gen_cast(llops, self.lowleveltype, v_ptr)
        return v_ptr


def _getinstancerepr(rtyper, classdef):
    # Almost a copy of rclass.getinstancerepr()
    if classdef.basedef:
        _getinstancerepr(rtyper, classdef.basedef)
    flavor = rmodel.getgcflavor(classdef)
    try:
        result = rtyper.instance_reprs[classdef, flavor]
    except KeyError:
        result = AstNodeRepr(rtyper, classdef, gcflavor=flavor)

        rtyper.instance_reprs[classdef, flavor] = result
        rtyper.add_pendingsetup(result)
    return result


class ArenaEntry(ExtRegistryEntry):
    _about_ = Arena

    def compute_result_annotation(self):
        return SomeArena(self.bookkeeper.getuniqueclassdef(Arena))

    def specialize_call(self, hop):
        return hop.r_result.rtyper_new(hop)
    

class AstEntry(ExtRegistryEntry):
    _about_ = tuple(_all_subclasses(ast.AST))

    def compute_result_annotation(self, *args):
        from rpython.annotator.argument import ArgumentsForTranslation
        classdef = self.bookkeeper.getuniqueclassdef(self.instance)
        s_init = classdef.classdesc.s_read_attribute('__init__')
        s_instance = SomeAstInstance(classdef)
        self.bookkeeper.emulate_pbc_call(classdef, s_init,
                                         [s_instance] + list(args))
        return s_instance

    def specialize_call(self, hop):
        from rpython.rtyper.rmodel import inputconst
        from rpython.rtyper.lltypesystem.lltype import Void, Ptr
        hop.exception_is_here()
        s_instance = hop.s_result
        object_type = hop.r_result.object_type
        classdef = s_instance.classdef
        rinstance = _getinstancerepr(hop.rtyper, classdef)
        v_instance = rinstance.new_instance(hop.llops, hop)
        # Call __init__
        s_init = classdef.classdesc.s_read_attribute('__init__')
        v_init = Constant("init-func-dummy")   # this value not really used
        hop2 = hop.copy()
        hop2.v_s_insertfirstarg(v_instance, s_instance)  # add 'instance'
        hop2.v_s_insertfirstarg(v_init, s_init)   # add 'initfunc'
        hop2.s_result = annmodel.s_None
        hop2.r_result = hop.rtyper.getrepr(hop2.s_result)
        hop2.dispatch()
        return v_instance

