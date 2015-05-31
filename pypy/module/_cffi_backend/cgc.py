from rpython.rlib import jit


@jit.dont_look_inside
def gc_weakrefs_build(ffi, w_cdata, w_destructor):
    from pypy.module._weakref import interp__weakref

    space = ffi.space
    if ffi.w_gc_wref_remove is None:
        ffi.gc_wref_dict = {}
        ffi.w_gc_wref_remove = space.getattr(space.wrap(ffi),
                                             space.wrap("__gc_wref_remove"))

    w_new_cdata = w_cdata.ctype.cast(w_cdata)
    assert w_new_cdata is not w_cdata

    w_ref = interp__weakref.make_weakref_with_callback(
        space,
        space.gettypefor(interp__weakref.W_Weakref),
        w_new_cdata,
        ffi.w_gc_wref_remove)

    ffi.gc_wref_dict[w_ref] = (w_destructor, w_cdata)
    return w_new_cdata


def gc_wref_remove(ffi, w_ref):
    (w_destructor, w_cdata) = ffi.gc_wref_dict.pop(w_ref)
    ffi.space.call_function(w_destructor, w_cdata)
