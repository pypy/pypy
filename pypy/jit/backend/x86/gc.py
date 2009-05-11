from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rclass
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86 import symbolic
from pypy.jit.backend.x86.runner import ConstDescr3


class GcLLDescription:
    def __init__(self, gcdescr, mixlevelann):
        self.gcdescr = gcdescr
    def _freeze_(self):
        return True

# ____________________________________________________________

class GcLLDescr_boehm(GcLLDescription):

    def __init__(self, gcdescr, mixlevelann):
        # grab a pointer to the Boehm 'malloc' function
        compilation_info = ExternalCompilationInfo(libraries=['gc'])
        malloc_fn_ptr = rffi.llexternal("GC_malloc",
                                        [lltype.Signed], # size_t, but good enough
                                        llmemory.GCREF,
                                        compilation_info=compilation_info,
                                        sandboxsafe=True,
                                        _nowrapper=True)
        self.funcptr_for_new = malloc_fn_ptr

    def sizeof(self, S, translate_support_code):
        size = symbolic.get_size(S, translate_support_code)
        return ConstDescr3(size, 0, False)

    def gc_malloc(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        return self.funcptr_for_new(size)

    def gc_malloc_array(self, arraydescr, num_elem):
        assert isinstance(arraydescr, ConstDescr3)
        size_of_field = arraydescr.v0
        ofs = arraydescr.v1
        size = ofs + (1 << size_of_field) * num_elem
        return self.funcptr_for_new(size)

    def args_for_new(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        return [size]

    def get_funcptr_for_new(self):
        return self.funcptr_for_new

# ____________________________________________________________

class GcLLDescr_framework(GcLLDescription):

    def __init__(self, gcdescr, mixlevelann):
        from pypy.rpython.memory.gc.base import choose_gc_from_config
        from pypy.rpython.memory.gctransform import framework
        self.translator = mixlevelann.rtyper.annotator.translator

        # make a TransformerLayoutBuilder and save it on the translator
        # where it can be fished and reused by the FrameworkGCTransformer
        self.layoutbuilder = framework.TransformerLayoutBuilder()
        self.translator._transformerlayoutbuilder_from_jit = self.layoutbuilder
        #GCClass, _ = choose_gc_from_config(gcdescr.config)

        # make a malloc function, with three arguments
        def malloc_basic(size, type_id, has_finalizer):
            return llop.do_malloc_fixedsize_clear(llmemory.GCREF,
                                                  type_id, size, True,
                                                  has_finalizer, False)
        self.malloc_basic = malloc_basic
        self.GC_MALLOC_BASIC = lltype.Ptr(lltype.FuncType(
            [lltype.Signed, lltype.Signed, lltype.Bool], llmemory.GCREF))

        assert gcdescr.config.translation.gcrootfinder == "asmgcc", (
            "with the framework GCs, you must use"
            " --gcrootfinder=asmgcc for now")

    def sizeof(self, S, translate_support_code):
        from pypy.rpython.memory.gctypelayout import weakpointer_offset
        assert translate_support_code, "required with the framework GC"
        size = symbolic.get_size(S, True)
        type_id = self.layoutbuilder.get_type_id(S)
        has_finalizer = bool(self.layoutbuilder.has_finalizer(S))
        assert weakpointer_offset(S) == -1     # XXX
        return ConstDescr3(size, type_id, has_finalizer)

    def gc_malloc(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        type_id = descrsize.v1
        has_finalizer = descrsize.flag2
        assert type_id > 0
        return self.malloc_basic(size, type_id, has_finalizer)

    def gc_malloc_array(self, arraydescr, num_elem):
        raise NotImplementedError

    def args_for_new(self, descrsize):
        assert isinstance(descrsize, ConstDescr3)
        size = descrsize.v0
        type_id = descrsize.v1
        has_finalizer = descrsize.flag2
        return [size, type_id, has_finalizer]

    def get_funcptr_for_new(self):
        return llhelper(self.GC_MALLOC_BASIC, self.malloc_basic)

# ____________________________________________________________

def get_ll_description(gcdescr, mixlevelann):
    if gcdescr is not None:
        name = gcdescr.config.translation.gctransformer
    else:
        name = "boehm"
    try:
        cls = globals()['GcLLDescr_' + name]
    except KeyError:
        raise NotImplementedError("GC transformer %r not supported by "
                                  "the x86 backend" % (name,))
    return cls(gcdescr, mixlevelann)
