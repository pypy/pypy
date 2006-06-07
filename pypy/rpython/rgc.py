from pypy.rpython.extregistry import ExtRegistryEntry
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
        from pypy.rpython.rmodel import SimplePointerRepr
        from pypy.rpython.memory.gc import X_POOL_PTR
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
        vlist = hop.inputargs(r_pool_ptr)
        return hop.genop('gc_x_swap_pool', vlist, resulttype = r_pool_ptr)


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
        r_gcobject = hop.args_r[0]
        if (not isinstance(r_gcobject.lowleveltype, lltype.Ptr) or
            r_gcobject.lowleveltype.TO._gckind != 'gc'):
            raise TyperError("gc_clone() can only clone a dynamically "
                             "allocated object;\ngot %r" % (r_gcobject,))
        from pypy.annotation import model as annmodel
        from pypy.rpython.memory.gc import X_CLONE, X_CLONE_PTR
        s_pool_ptr = annmodel.SomeExternalObject(GcPool)
        r_pool_ptr = hop.rtyper.getrepr(s_pool_ptr)
        r_tuple = hop.r_result

        c_CLONE       = hop.inputconst(lltype.Void, X_CLONE)
        c_gcobjectptr = hop.inputconst(lltype.Void, "gcobjectptr")
        c_pool        = hop.inputconst(lltype.Void, "pool")

        v_gcobject, v_pool = hop.inputargs(hop.args_r[0], r_pool_ptr)
        v_gcobjectptr = hop.genop('cast_opaque_ptr', [v_gcobject],
                                  resulttype = llmemory.GCREF)
        v_clonedata = hop.genop('malloc', [c_CLONE],
                                resulttype = X_CLONE_PTR)
        hop.genop('setfield', [v_clonedata, c_gcobjectptr, v_gcobjectptr])
        hop.genop('setfield', [v_clonedata, c_pool, v_pool])
        hop.genop('gc_x_clone', [v_clonedata])
        v_gcobjectptr = hop.genop('getfield', [v_clonedata, c_gcobjectptr],
                                  resulttype = llmemory.GCREF)
        v_pool        = hop.genop('getfield', [v_clonedata, c_pool],
                                  resulttype = r_pool_ptr)
        v_gcobject = hop.genop('cast_opaque_ptr', [v_gcobjectptr],
                               resulttype = r_tuple.items_r[0])
        return rtuple.newtuple(hop.llops, r_tuple, [v_gcobject, v_pool])

# Support for collection.
import gc

class CollectEntry(ExtRegistryEntry):
    _about_ = gc.collect

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        return hop.genop('gc__collect', [], resulttype=hop.r_result)
    

