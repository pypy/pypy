import gc
from pypy.rpython.extregistry import ExtRegistryEntry
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

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.genop('gc__collect', [], resulttype=hop.r_result)
    
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

def can_move(p):
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

def malloc_nonmovable(TP, n=None):
    """ Allocate a non-moving buffer or return nullptr.
    When running directly, will pretend that gc is always
    moving (might be configurable in a future)
    """
    from pypy.rpython.lltypesystem import lltype
    return lltype.nullptr(TP)

class MallocNonMovingEntry(ExtRegistryEntry):
    _about_ = malloc_nonmovable

    def compute_result_annotation(self, s_TP, s_n=None):
        # basically return the same as malloc
        from pypy.annotation.builtin import malloc
        return malloc(s_TP, s_n)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        # XXX assume flavor and zero to be None by now
        assert hop.args_s[0].is_constant()
        vlist = [hop.inputarg(lltype.Void, arg=0)]
        opname = 'malloc_nonmovable'
        flags = {'flavor': 'gc'}
        vlist.append(hop.inputconst(lltype.Void, flags))

        if hop.nb_args == 2:
            vlist.append(hop.inputarg(lltype.Signed, arg=1))
            opname += '_varsize'

        hop.exception_cannot_occur()
        return hop.genop(opname, vlist, resulttype = hop.r_result.lowleveltype)

def resizable_buffer_of_shape(T, init_size):
    """ Pre-allocates structure of type T (varsized) with possibility
    to reallocate it further by resize_buffer.
    """
    from pypy.rpython.lltypesystem import lltype
    return lltype.malloc(T, init_size)

class ResizableBufferOfShapeEntry(ExtRegistryEntry):
    _about_ = resizable_buffer_of_shape

    def compute_result_annotation(self, s_T, s_init_size):
        from pypy.annotation import model as annmodel
        from pypy.rpython.lltypesystem import rffi, lltype
        assert s_T.is_constant()
        assert isinstance(s_init_size, annmodel.SomeInteger)
        T = s_T.const
        # limit ourselves to structs and to a fact that var-sized element
        # does not contain pointers.
        assert isinstance(T, lltype.Struct)
        assert isinstance(getattr(T, T._arrayfld).OF, lltype.Primitive)
        return annmodel.SomePtr(lltype.Ptr(T))

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        flags = {'flavor': 'gc'}
        vlist = [hop.inputarg(lltype.Void, 0),
                 hop.inputconst(lltype.Void, flags),
                 hop.inputarg(lltype.Signed, 1)]
        hop.exception_is_here()
        return hop.genop('malloc_resizable_buffer', vlist,
                         resulttype=hop.r_result.lowleveltype)

def resize_buffer(ptr, old_size, new_size):
    """ Resize raw buffer returned by resizable_buffer_of_shape to new size
    """
    from pypy.rpython.lltypesystem import lltype
    T = lltype.typeOf(ptr).TO
    arrayfld = T._arrayfld
    arr = getattr(ptr, arrayfld)
    # we don't have any realloc on top of cpython
    new_ptr = lltype.malloc(T, new_size)
    new_ar = getattr(new_ptr, arrayfld)
    for i in range(old_size):
        new_ar[i] = arr[i]
    return new_ptr

class ResizeBufferEntry(ExtRegistryEntry):
    _about_ = resize_buffer

    def compute_result_annotation(self, s_ptr, s_old_size, s_new_size):
        from pypy.annotation import model as annmodel
        from pypy.rpython.lltypesystem import rffi
        assert isinstance(s_ptr, annmodel.SomePtr)
        assert isinstance(s_new_size, annmodel.SomeInteger)
        assert isinstance(s_old_size, annmodel.SomeInteger)
        return s_ptr

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        vlist = [hop.inputarg(hop.args_r[0], 0),
                 hop.inputarg(lltype.Signed, 1),
                 hop.inputarg(lltype.Signed, 2)]
        hop.exception_is_here()
        return hop.genop('resize_buffer', vlist,
                         resulttype=hop.r_result.lowleveltype)

def finish_building_buffer(ptr, final_size):
    """ Finish building resizable buffer returned by resizable_buffer_of_shape
    """
    return ptr

class FinishBuildingBufferEntry(ExtRegistryEntry):
    _about_ = finish_building_buffer

    def compute_result_annotation(self, s_arr, s_final_size):
        from pypy.annotation.model import SomePtr, s_ImpossibleValue,\
             SomeInteger
        assert isinstance(s_arr, SomePtr)
        assert isinstance(s_final_size, SomeInteger)
        return s_arr

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        vlist = [hop.inputarg(hop.args_r[0], 0),
                 hop.inputarg(hop.args_r[1], 1)]
        hop.exception_cannot_occur()
        return hop.genop('finish_building_buffer', vlist,
                         resulttype=hop.r_result.lowleveltype)
