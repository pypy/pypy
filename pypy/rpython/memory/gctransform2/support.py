from pypy.rpython.lltypesystem import lltype

def var_ispyobj(var):
    if hasattr(var, 'concretetype'):
        if isinstance(var.concretetype, lltype.Ptr):
            return var.concretetype.TO._gckind == 'cpy'
        else:
            return False
    else:
        # assume PyObjPtr
        return True

PyObjPtr = lltype.Ptr(lltype.PyObject)

def find_gc_ptrs_in_type(TYPE):
    if isinstance(TYPE, lltype.Array):
        return find_gc_ptrs_in_type(TYPE.OF)
    elif isinstance(TYPE, lltype.Struct):
        result = []
        for name in TYPE._names:
            result.extend(find_gc_ptrs_in_type(TYPE._flds[name]))
        return result
    elif isinstance(TYPE, lltype.Ptr) and TYPE._needsgc():
        return [TYPE]
    elif isinstance(TYPE, lltype.GcOpaqueType):
        # heuristic: in theory the same problem exists with OpaqueType, but
        # we use OpaqueType for other things too that we know are safely
        # empty of further gc pointers
        raise Exception("don't know what is in %r" % (TYPE,))
    else:
        return []
