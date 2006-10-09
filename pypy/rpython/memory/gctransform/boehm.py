from pypy.rpython.memory.gctransform.transform import GCTransformer
from pypy.rpython.memory.gctransform.support import type_contains_pyobjs, \
     get_rtti, _static_deallocator_body_for_type, LLTransformerOp, ll_call_destructor
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop

class BoehmGCTransformer(GCTransformer):
    def __init__(self, translator, inline=False):
        super(BoehmGCTransformer, self).__init__(translator, inline=inline)
        self.finalizer_funcptrs = {}

    def push_alive_nopyobj(self, var, llops):
        pass

    def pop_alive_nopyobj(self, var, llops):
        pass

    def gct_gc_protect(self, hop):
        """ for boehm it is enough to do nothing"""
        pass

    def gct_gc_unprotect(self, hop):
        """ for boehm it is enough to do nothing"""
        pass

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]

        rtti = get_rtti(TYPE)
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            destrptr = None
            DESTR_ARG = None

        if type_contains_pyobjs(TYPE):
            if destrptr:
                raise Exception("can't mix PyObjects and __del__ with Boehm")

            static_body = '\n'.join(_static_deallocator_body_for_type('v', TYPE))
            d = {'pop_alive': LLTransformerOp(self.pop_alive),
                 'PTR_TYPE':lltype.Ptr(TYPE),
                 'cast_adr_to_ptr': llmemory.cast_adr_to_ptr}
            src = ("def ll_finalizer(addr):\n"
                   "    v = cast_adr_to_ptr(addr, PTR_TYPE)\n"
                   "%s\n")%(static_body,)
            exec src in d
            fptr = self.annotate_helper(d['ll_finalizer'], [llmemory.Address], lltype.Void)
        elif destrptr:
            EXC_INSTANCE_TYPE = self.translator.rtyper.exceptiondata.lltype_of_exception_value
            def ll_finalizer(addr):
                exc_instance = llop.gc_fetch_exception(EXC_INSTANCE_TYPE)
                v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                ll_call_destructor(destrptr, v)
                llop.gc_restore_exception(lltype.Void, exc_instance)
            fptr = self.annotate_helper(ll_finalizer, [llmemory.Address], lltype.Void)
        else:
            fptr = None

        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

