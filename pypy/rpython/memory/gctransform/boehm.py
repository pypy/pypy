from pypy.rpython.memory.gctransform.transform import GCTransformer
from pypy.rpython.memory.gctransform.support import type_contains_pyobjs, \
     get_rtti, _static_deallocator_body_for_type, LLTransformerOp, ll_call_destructor
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython import rmodel
from pypy.rlib.rarithmetic import ovfcheck
from pypy.objspace.flow.model import Constant

class BoehmGCTransformer(GCTransformer):
    FINALIZER_PTR = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Void))

    def __init__(self, translator, inline=False):
        super(BoehmGCTransformer, self).__init__(translator, inline=inline)
        self.finalizer_funcptrs = {}
        memoryError = MemoryError()

        def ll_malloc_fixedsize(size, finalizer):
            result = llop.boehm_malloc(llmemory.Address, size)
            if not result:
                raise memoryError
            if finalizer: # XXX runtime check here is bad?
                llop.boehm_register_finalizer(lltype.Void, result, finalizer)
            return result
        def ll_malloc_fixedsize_atomic(size, finalizer):
            result = llop.boehm_malloc_atomic(llmemory.Address, size)
            if not result:
                raise memoryError
            if finalizer: # XXX runtime check here is bad?
                llop.boehm_register_finalizer(lltype.Void, result, finalizer)
            return result
        # XXX, do we need/want an atomic version of this function?
        def ll_malloc_varsize_no_length(length, size, itemsize):
            try:
                varsize = ovfcheck(itemsize * length)
                tot_size = ovfcheck(size + varsize)
            except OverflowError:
                raise memoryError
            result = llop.boehm_malloc(llmemory.Address, tot_size)
            if not result:
                raise memoryError
            return result
        def ll_malloc_varsize(length, size, itemsize, lengthoffset):
            result = ll_malloc_varsize_no_length(length, size, itemsize)
            (result + lengthoffset).signed[0] = length
            return result

        if self.translator:
            self.malloc_fixedsize_ptr = self.inittime_helper(
                ll_malloc_fixedsize, [lltype.Signed, self.FINALIZER_PTR], llmemory.Address)
            self.malloc_fixedsize_atomic_ptr = self.inittime_helper(
                ll_malloc_fixedsize_atomic, [lltype.Signed, self.FINALIZER_PTR], llmemory.Address)
            self.malloc_varsize_no_length_ptr = self.inittime_helper(
                ll_malloc_varsize_no_length, [lltype.Signed]*3, llmemory.Address, inline=False)
            self.malloc_varsize_ptr = self.inittime_helper(
                ll_malloc_varsize, [lltype.Signed]*4, llmemory.Address, inline=False)
            self.mixlevelannotator.finish()   # for now

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

    def gct_malloc(self, hop):
        TYPE = hop.spaceop.result.concretetype.TO
        assert not TYPE._is_varsize()
        c_size = rmodel.inputconst(lltype.Signed, llmemory.sizeof(TYPE))
        if TYPE._is_atomic():
            funcptr = self.malloc_fixedsize_atomic_ptr
        else:
            funcptr = self.malloc_fixedsize_ptr
        c_finalizer_ptr = Constant(self.finalizer_funcptr_for_type(TYPE), self.FINALIZER_PTR)
        v_raw = hop.genop("direct_call",
                          [funcptr, c_size, c_finalizer_ptr],
                          resulttype=llmemory.Address)
        hop.cast_result(v_raw)

    # XXX In theory this is wrong:
    gct_zero_malloc = gct_malloc

    def gct_malloc_varsize(self, hop):
        def intconst(c): return rmodel.inputconst(lltype.Signed, c)

        op = hop.spaceop
        TYPE = op.result.concretetype.TO
        assert TYPE._is_varsize()

        assert not self.finalizer_funcptr_for_type(TYPE)

        if isinstance(TYPE, lltype.Struct):
            ARRAY = TYPE._flds[TYPE._arrayfld]
        else:
            ARRAY = TYPE
        assert isinstance(ARRAY, lltype.Array)
        if ARRAY._hints.get('isrpystring', False):
            c_const_size = intconst(llmemory.sizeof(TYPE, 1))
        else:
            c_const_size = intconst(llmemory.sizeof(TYPE, 0))
        c_item_size = intconst(llmemory.sizeof(ARRAY.OF))

        if ARRAY._hints.get("nolength", False):
            v_raw = hop.genop("direct_call",
                               [self.malloc_varsize_no_length_ptr, op.args[-1],
                                c_const_size, c_item_size],
                               resulttype=llmemory.Address)
        else:
            if isinstance(TYPE, lltype.Struct):
                offset_to_length = llmemory.FieldOffset(TYPE, TYPE._arrayfld) + \
                                   llmemory.ArrayLengthOffset(ARRAY)
            else:
                offset_to_length = llmemory.ArrayLengthOffset(ARRAY)
            v_raw = hop.genop("direct_call",
                               [self.malloc_varsize_ptr, op.args[-1],
                                c_const_size, c_item_size, intconst(offset_to_length)],
                               resulttype=llmemory.Address)
        hop.cast_result(v_raw)

    gct_zero_malloc_varsize = gct_malloc_varsize

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
            fptr = lltype.nullptr(self.FINALIZER_PTR.TO)

        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

