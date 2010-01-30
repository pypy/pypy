from pypy.rpython.memory.gctransform.transform import GCTransformer, mallocHelpers
from pypy.rpython.memory.gctransform.support import type_contains_pyobjs, \
     get_rtti, _static_deallocator_body_for_type, LLTransformerOp, ll_call_destructor
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import rffi
from pypy.rpython import rmodel

class BoehmGCTransformer(GCTransformer):
    malloc_zero_filled = True
    FINALIZER_PTR = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Void))
    HDR = lltype.Struct("header", ("hash", lltype.Signed))

    def __init__(self, translator, inline=False):
        super(BoehmGCTransformer, self).__init__(translator, inline=inline)
        self.finalizer_funcptrs = {}

        atomic_mh = mallocHelpers()
        atomic_mh.allocate = lambda size: llop.boehm_malloc_atomic(llmemory.Address, size)
        ll_malloc_fixedsize_atomic = atomic_mh._ll_malloc_fixedsize

        mh = mallocHelpers()
        mh.allocate = lambda size: llop.boehm_malloc(llmemory.Address, size)
        ll_malloc_fixedsize = mh._ll_malloc_fixedsize

        # XXX, do we need/want an atomic version of this function?
        ll_malloc_varsize_no_length = mh.ll_malloc_varsize_no_length
        ll_malloc_varsize = mh.ll_malloc_varsize

        HDRPTR = lltype.Ptr(self.HDR)

        def ll_identityhash(addr):
            obj = llmemory.cast_adr_to_ptr(addr, HDRPTR)
            h = obj.hash
            if h == 0:
                obj.hash = h = ~llmemory.cast_adr_to_int(addr)
            return h

        if self.translator:
            self.malloc_fixedsize_ptr = self.inittime_helper(
                ll_malloc_fixedsize, [lltype.Signed], llmemory.Address)
            self.malloc_fixedsize_atomic_ptr = self.inittime_helper(
                ll_malloc_fixedsize_atomic, [lltype.Signed], llmemory.Address)
            self.malloc_varsize_no_length_ptr = self.inittime_helper(
                ll_malloc_varsize_no_length, [lltype.Signed]*3, llmemory.Address, inline=False)
            self.malloc_varsize_ptr = self.inittime_helper(
                ll_malloc_varsize, [lltype.Signed]*4, llmemory.Address, inline=False)
            self.weakref_create_ptr = self.inittime_helper(
                ll_weakref_create, [llmemory.Address], llmemory.WeakRefPtr,
                inline=False)
            self.weakref_deref_ptr = self.inittime_helper(
                ll_weakref_deref, [llmemory.WeakRefPtr], llmemory.Address)
            self.identityhash_ptr = self.inittime_helper(
                ll_identityhash, [llmemory.Address], lltype.Signed,
                inline=False)
            self.mixlevelannotator.finish()   # for now
            self.mixlevelannotator.backend_optimize()

    def push_alive_nopyobj(self, var, llops):
        pass

    def pop_alive_nopyobj(self, var, llops):
        pass

    def gct_fv_gc_malloc(self, hop, flags, TYPE, c_size):
        # XXX same behavior for zero=True: in theory that's wrong
        if TYPE._is_atomic():
            funcptr = self.malloc_fixedsize_atomic_ptr
        else:
            funcptr = self.malloc_fixedsize_ptr
        v_raw = hop.genop("direct_call",
                          [funcptr, c_size],
                          resulttype=llmemory.Address)
        finalizer_ptr = self.finalizer_funcptr_for_type(TYPE)
        if finalizer_ptr:
            c_finalizer_ptr = Constant(finalizer_ptr, self.FINALIZER_PTR)
            hop.genop("boehm_register_finalizer", [v_raw, c_finalizer_ptr])
        return v_raw

    def gct_fv_gc_malloc_varsize(self, hop, flags, TYPE, v_length, c_const_size, c_item_size,
                                                                   c_offset_to_length):
        # XXX same behavior for zero=True: in theory that's wrong        
        if c_offset_to_length is None:
            v_raw = hop.genop("direct_call",
                               [self.malloc_varsize_no_length_ptr, v_length,
                                c_const_size, c_item_size],
                               resulttype=llmemory.Address)
        else:
            v_raw = hop.genop("direct_call",
                               [self.malloc_varsize_ptr, v_length,
                                c_const_size, c_item_size, c_offset_to_length],
                               resulttype=llmemory.Address)
        return v_raw

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
            fptr = self.annotate_finalizer(d['ll_finalizer'], [llmemory.Address], lltype.Void)
        elif destrptr:
            EXC_INSTANCE_TYPE = self.translator.rtyper.exceptiondata.lltype_of_exception_value
            def ll_finalizer(addr):
                exc_instance = llop.gc_fetch_exception(EXC_INSTANCE_TYPE)
                v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                ll_call_destructor(destrptr, v)
                llop.gc_restore_exception(lltype.Void, exc_instance)
            fptr = self.annotate_finalizer(ll_finalizer, [llmemory.Address], lltype.Void)
        else:
            fptr = lltype.nullptr(self.FINALIZER_PTR.TO)

        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

    def gct_weakref_create(self, hop):
        v_instance, = hop.spaceop.args
        v_addr = hop.genop("cast_ptr_to_adr", [v_instance],
                           resulttype=llmemory.Address)
        v_wref = hop.genop("direct_call",
                           [self.weakref_create_ptr, v_addr],
                           resulttype=llmemory.WeakRefPtr)
        hop.cast_result(v_wref)

    def gct_weakref_deref(self, hop):
        v_wref, = hop.spaceop.args
        v_addr = hop.genop("direct_call",
                           [self.weakref_deref_ptr, v_wref],
                           resulttype=llmemory.Address)
        hop.cast_result(v_addr)

    def gct_gc_writebarrier_before_copy(self, hop):
        # no write barrier needed
        op = hop.spaceop
        hop.genop("same_as",
                  [rmodel.inputconst(lltype.Bool, True)],
                  resultvar=op.result)

    def gct_gc_identityhash(self, hop):
        v_obj = hop.spaceop.args[0]
        v_adr = hop.genop("cast_ptr_to_adr", [v_obj],
                          resulttype=llmemory.Address)
        hop.genop("direct_call", [self.identityhash_ptr, v_adr],
                  resultvar=hop.spaceop.result)

    def gct_gc_id(self, hop):
        # this is the logic from the HIDE_POINTER macro in <gc/gc.h>
        v_int = hop.genop('cast_ptr_to_int', [hop.spaceop.args[0]],
                          resulttype = lltype.Signed)
        hop.genop('int_invert', [v_int], resultvar=hop.spaceop.result)


########## weakrefs ##########
# Boehm: weakref objects are small structures containing only a Boehm
# disappearing link.  We don't have to hide the link's value with
# HIDE_POINTER(), because we explicitly use GC_MALLOC_ATOMIC().

WEAKLINK = lltype.FixedSizeArray(llmemory.Address, 1)
sizeof_weakreflink = llmemory.sizeof(WEAKLINK)
empty_weaklink = lltype.malloc(WEAKLINK, immortal=True)
empty_weaklink[0] = llmemory.NULL

def ll_weakref_create(targetaddr):
    link = llop.boehm_malloc_atomic(llmemory.Address, sizeof_weakreflink)
    if not link:
        raise MemoryError
    plink = llmemory.cast_adr_to_ptr(link, lltype.Ptr(WEAKLINK))
    plink[0] = targetaddr
    llop.boehm_disappearing_link(lltype.Void, link, targetaddr)
    return llmemory.cast_ptr_to_weakrefptr(plink)

def ll_weakref_deref(wref):
    plink = llmemory.cast_weakrefptr_to_ptr(lltype.Ptr(WEAKLINK), wref)
    return plink[0]

def convert_weakref_to(targetptr):
    # Prebuilt weakrefs don't really need to be weak at all,
    # but we need to emulate the structure expected by ll_weakref_deref().
    # This is essentially the same code as in ll_weakref_create(), but I'm
    # not sure trying to share it is worth the hassle...
    if not targetptr:
        return empty_weaklink
    else:
        plink = lltype.malloc(WEAKLINK, immortal=True)
        plink[0] = llmemory.cast_ptr_to_adr(targetptr)
        return plink
