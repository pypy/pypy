import gc
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.objectmodel import we_are_translated

# ____________________________________________________________
# General GC features

collect = gc.collect

def set_max_heap_size(nbytes):
    """Limit the heap size to n bytes.
    So far only implemented by the Boehm GC and the semispace/generation GCs.
    """
    pass

# ____________________________________________________________
# Framework GC features

class GcPool(object):
    pass

def gc_swap_pool(newpool):
    """Set newpool as the current pool (create one if newpool is None).
    All malloc'ed objects are put into the current pool;this is a
    way to separate objects depending on when they were allocated.
    """
    raise NotImplementedError("only works in stacklessgc translated versions")

def gc_clone(gcobject, pool):
    """Recursively clone the gcobject and everything it points to,
    directly or indirectly -- but stops at objects that are not
    in the specified pool.  Pool can be None to mean the current one.
    A new pool is built to contain the copies.  Return (newobject, newpool).
    """
    raise NotImplementedError("only works in stacklessgc translated versions")

# ____________________________________________________________
# Annotation and specialization

class GcPoolEntry(ExtRegistryEntry):
    "Link GcPool to its Repr."
    _type_ = GcPool

    def get_repr(self, rtyper, s_pool):
        config = rtyper.getconfig()
        # if the gc policy doesn't support allocation pools, lltype
        # pools as Void.
        if config.translation.gc != 'marksweep':
            from pypy.annotation.model import s_None
            return rtyper.getrepr(s_None)
        else:
            from pypy.rpython.rmodel import SimplePointerRepr
            from pypy.rpython.memory.gc.marksweep import X_POOL_PTR
            return SimplePointerRepr(X_POOL_PTR)


class SwapPoolFnEntry(ExtRegistryEntry):
    "Annotation and specialization of gc_swap_pool()."
    _about_ = gc_swap_pool

    def compute_result_annotation(self, s_newpool):
        from pypy.annotation import model as annmodel
        return annmodel.SomeExternalObject(GcPool)

    def specialize_call(self, hop):
        from pypy.annotation import model as annmodel
        s_pool_ptr = annmodel.SomeExternalObject(GcPool)
        r_pool_ptr = hop.rtyper.getrepr(s_pool_ptr)

        opname = 'gc_x_swap_pool'
        config = hop.rtyper.getconfig()
        if config.translation.gc != 'marksweep':
            # when the gc policy doesn't support pools, just return
            # the argument (which is lltyped as Void anyway)
            opname = 'same_as'
            
        s_pool_ptr = annmodel.SomeExternalObject(GcPool)
        r_pool_ptr = hop.rtyper.getrepr(s_pool_ptr)
        vlist = hop.inputargs(r_pool_ptr)
        return hop.genop(opname, vlist, resulttype = r_pool_ptr)

def _raise():
    raise RuntimeError

class CloneFnEntry(ExtRegistryEntry):
    "Annotation and specialization of gc_clone()."
    _about_ = gc_clone

    def compute_result_annotation(self, s_gcobject, s_pool):
        from pypy.annotation import model as annmodel
        return annmodel.SomeTuple([s_gcobject,
                                   annmodel.SomeExternalObject(GcPool)])

    def specialize_call(self, hop):
        from pypy.rpython.error import TyperError
        from pypy.rpython.lltypesystem import lltype, llmemory, rtuple
        from pypy.annotation import model as annmodel
        from pypy.rpython.memory.gc.marksweep import X_CLONE, X_CLONE_PTR

        config = hop.rtyper.getconfig()
        if config.translation.gc != 'marksweep':
            # if the gc policy does not support allocation pools,
            # gc_clone always raises RuntimeError
            hop.exception_is_here()
            hop.gendirectcall(_raise)
            s_pool_ptr = annmodel.SomeExternalObject(GcPool)
            r_pool_ptr = hop.rtyper.getrepr(s_pool_ptr)
            r_tuple = hop.r_result
            v_gcobject, v_pool = hop.inputargs(hop.args_r[0], r_pool_ptr)
            return rtuple.newtuple(hop.llops, r_tuple, [v_gcobject, v_pool])

        r_gcobject = hop.args_r[0]
        if (not isinstance(r_gcobject.lowleveltype, lltype.Ptr) or
            r_gcobject.lowleveltype.TO._gckind != 'gc'):
            raise TyperError("gc_clone() can only clone a dynamically "
                             "allocated object;\ngot %r" % (r_gcobject,))
        s_pool_ptr = annmodel.SomeExternalObject(GcPool)
        r_pool_ptr = hop.rtyper.getrepr(s_pool_ptr)
        r_tuple = hop.r_result

        c_CLONE       = hop.inputconst(lltype.Void, X_CLONE)
        c_flags       = hop.inputconst(lltype.Void, {'flavor': 'gc'})
        c_gcobjectptr = hop.inputconst(lltype.Void, "gcobjectptr")
        c_pool        = hop.inputconst(lltype.Void, "pool")

        v_gcobject, v_pool = hop.inputargs(hop.args_r[0], r_pool_ptr)
        v_gcobjectptr = hop.genop('cast_opaque_ptr', [v_gcobject],
                                  resulttype = llmemory.GCREF)
        v_clonedata = hop.genop('malloc', [c_CLONE, c_flags],
                                resulttype = X_CLONE_PTR)
        hop.genop('setfield', [v_clonedata, c_gcobjectptr, v_gcobjectptr])
        hop.genop('setfield', [v_clonedata, c_pool, v_pool])
        hop.exception_is_here()
        hop.genop('gc_x_clone', [v_clonedata])
        v_gcobjectptr = hop.genop('getfield', [v_clonedata, c_gcobjectptr],
                                  resulttype = llmemory.GCREF)
        v_pool        = hop.genop('getfield', [v_clonedata, c_pool],
                                  resulttype = r_pool_ptr)
        v_gcobject = hop.genop('cast_opaque_ptr', [v_gcobjectptr],
                               resulttype = r_tuple.items_r[0])
        return rtuple.newtuple(hop.llops, r_tuple, [v_gcobject, v_pool])

# Support for collection.

class CollectEntry(ExtRegistryEntry):
    _about_ = gc.collect

    def compute_result_annotation(self, s_gen=None):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype        
        hop.exception_cannot_occur()
        args_v = []
        if len(hop.args_s) == 1:
            args_v = hop.inputargs(lltype.Signed)
        return hop.genop('gc__collect', args_v, resulttype=hop.r_result)
    
class SetMaxHeapSizeEntry(ExtRegistryEntry):
    _about_ = set_max_heap_size

    def compute_result_annotation(self, s_nbytes):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        [v_nbytes] = hop.inputargs(lltype.Signed)
        hop.exception_cannot_occur()
        return hop.genop('gc_set_max_heap_size', [v_nbytes],
                         resulttype=lltype.Void)

def can_move(p):    # NB. must not be called with NULL pointers
    return True

class CanMoveEntry(ExtRegistryEntry):
    _about_ = can_move

    def compute_result_annotation(self, s_p):
        from pypy.annotation import model as annmodel
        return annmodel.SomeBool()

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        hop.exception_cannot_occur()
        return hop.genop('gc_can_move', hop.args_v, resulttype=hop.r_result)

def _heap_stats():
    raise NotImplementedError # can't be run directly

class DumpHeapEntry(ExtRegistryEntry):
    _about_ = _heap_stats

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        from pypy.rpython.memory.gc.base import ARRAY_TYPEID_MAP
        from pypy.rpython.lltypesystem import lltype
        return annmodel.SomePtr(lltype.Ptr(ARRAY_TYPEID_MAP))

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.memory.gc.base import ARRAY_TYPEID_MAP
        from pypy.rpython.lltypesystem import lltype
        hop.exception_is_here()
        return hop.genop('gc_heap_stats', [], resulttype=hop.r_result)

def malloc_nonmovable(TP, n=None, zero=False):
    """ Allocate a non-moving buffer or return nullptr.
    When running directly, will pretend that gc is always
    moving (might be configurable in a future)
    """
    from pypy.rpython.lltypesystem import lltype
    return lltype.nullptr(TP)

class MallocNonMovingEntry(ExtRegistryEntry):
    _about_ = malloc_nonmovable

    def compute_result_annotation(self, s_TP, s_n=None, s_zero=None):
        # basically return the same as malloc
        from pypy.annotation.builtin import malloc
        return malloc(s_TP, s_n, s_zero=s_zero)

    def specialize_call(self, hop, i_zero=None):
        from pypy.rpython.lltypesystem import lltype
        # XXX assume flavor and zero to be None by now
        assert hop.args_s[0].is_constant()
        vlist = [hop.inputarg(lltype.Void, arg=0)]
        opname = 'malloc_nonmovable'
        flags = {'flavor': 'gc'}
        if i_zero is not None:
            flags['zero'] = hop.args_s[i_zero].const
            nb_args = hop.nb_args - 1
        else:
            nb_args = hop.nb_args
        vlist.append(hop.inputconst(lltype.Void, flags))

        if nb_args == 2:
            vlist.append(hop.inputarg(lltype.Signed, arg=1))
            opname += '_varsize'

        hop.exception_cannot_occur()
        return hop.genop(opname, vlist, resulttype = hop.r_result.lowleveltype)

def ll_arraycopy(source, dest, source_start, dest_start, length):
    from pypy.rpython.lltypesystem.lloperation import llop
    from pypy.rpython.lltypesystem import lltype, llmemory
    from pypy.rlib.objectmodel import keepalive_until_here

    # supports non-overlapping copies only
    if not we_are_translated():
        if source == dest:
            assert (source_start + length <= dest_start or
                    dest_start + length <= source_start)

    TP = lltype.typeOf(source).TO
    assert TP == lltype.typeOf(dest).TO
    if isinstance(TP.OF, lltype.Ptr) and TP.OF.TO._gckind == 'gc':
        # perform a write barrier that copies necessary flags from
        # source to dest
        if not llop.gc_writebarrier_before_copy(lltype.Bool, source, dest):
            # if the write barrier is not supported, copy by hand
            for i in range(length):
                dest[i + dest_start] = source[i + source_start]
            return
    source_addr = llmemory.cast_ptr_to_adr(source)
    dest_addr   = llmemory.cast_ptr_to_adr(dest)
    cp_source_addr = (source_addr + llmemory.itemoffsetof(TP, 0) +
                      llmemory.sizeof(TP.OF) * source_start)
    cp_dest_addr = (dest_addr + llmemory.itemoffsetof(TP, 0) +
                    llmemory.sizeof(TP.OF) * dest_start)
    
    llmemory.raw_memcopy(cp_source_addr, cp_dest_addr,
                         llmemory.sizeof(TP.OF) * length)
    keepalive_until_here(source)
    keepalive_until_here(dest)
ll_arraycopy._annenforceargs_ = [None, None, int, int, int]
ll_arraycopy._annspecialcase_ = 'specialize:ll'
ll_arraycopy._jit_look_inside_ = False

def ll_shrink_array(p, smallerlength):
    from pypy.rpython.lltypesystem.lloperation import llop
    from pypy.rpython.lltypesystem import lltype, llmemory
    from pypy.rlib.objectmodel import keepalive_until_here

    if llop.shrink_array(lltype.Bool, p, smallerlength):
        return p    # done by the GC
    # XXX we assume for now that the type of p is GcStruct containing a
    # variable array, with no further pointers anywhere, and exactly one
    # field in the fixed part -- like STR and UNICODE.

    TP = lltype.typeOf(p).TO
    newp = lltype.malloc(TP, smallerlength)

    assert len(TP._names) == 2
    field = getattr(p, TP._names[0])
    setattr(newp, TP._names[0], field)

    ARRAY = getattr(TP, TP._arrayfld)
    offset = (llmemory.offsetof(TP, TP._arrayfld) +
              llmemory.itemoffsetof(ARRAY, 0))
    source_addr = llmemory.cast_ptr_to_adr(p)    + offset
    dest_addr   = llmemory.cast_ptr_to_adr(newp) + offset
    llmemory.raw_memcopy(source_addr, dest_addr, 
                         llmemory.sizeof(ARRAY.OF) * smallerlength)

    keepalive_until_here(p)
    keepalive_until_here(newp)
    return newp
ll_shrink_array._annspecialcase_ = 'specialize:ll'
ll_shrink_array._jit_look_inside_ = False


def no_collect(func):
    func._dont_inline_ = True
    func._gc_no_collect_ = True
    return func
