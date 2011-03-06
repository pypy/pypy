from pypy.rlib import rgc
from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import wrap_oserror, OperationError
from pypy.rlib.objectmodel import we_are_translated


class W_GcRef(Wrappable):
    def __init__(self, gcref):
        self.gcref = gcref

W_GcRef.typedef = TypeDef("GcRef")


def try_cast_gcref_to_w_root(gcref):
    w_obj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
    # Ignore the instances of W_Root that are not really valid as Python
    # objects.  There is e.g. WeakrefLifeline in module/_weakref that
    # inherits from W_Root for internal reasons.  Such instances don't
    # have a typedef at all (or have a null typedef after translation).
    if not we_are_translated():
        if not hasattr(w_obj, 'typedef'):
            return None
    else:
        if w_obj is None or not w_obj.typedef:
            return None
    return w_obj

def wrap(space, gcref):
    w_obj = try_cast_gcref_to_w_root(gcref)
    if w_obj is None:
        w_obj = space.wrap(W_GcRef(gcref))
    return w_obj

def unwrap(space, w_obj):
    gcrefobj = space.interpclass_w(w_obj)
    if isinstance(gcrefobj, W_GcRef):
        gcref = gcrefobj.gcref
    else:
        gcref = rgc.cast_instance_to_gcref(w_obj)
    return gcref

def missing_operation(space):
    return OperationError(space.w_NotImplementedError,
                          space.wrap("operation not implemented by this GC"))

def get_rpy_roots(space):
    lst = rgc.get_rpy_roots()
    if lst is None:
        raise missing_operation(space)
    return space.newlist([wrap(space, gcref) for gcref in lst if gcref])

def get_rpy_referents(space, w_obj):
    """Return a list of all the referents, as reported by the GC.
    This is likely to contain a lot of GcRefs."""
    gcref = unwrap(space, w_obj)
    lst = rgc.get_rpy_referents(gcref)
    if lst is None:
        raise missing_operation(space)
    return space.newlist([wrap(space, gcref) for gcref in lst])

def get_rpy_memory_usage(space, w_obj):
    """Return the memory usage of just the given object or GcRef.
    This does not include the internal structures of the object."""
    gcref = unwrap(space, w_obj)
    size = rgc.get_rpy_memory_usage(gcref)
    if size < 0:
        raise missing_operation(space)
    return space.wrap(size)

def get_rpy_type_index(space, w_obj):
    """Return an integer identifying the RPython type of the given
    object or GcRef.  The number starts at 1; it is an index in the
    file typeids.txt produced at translation."""
    gcref = unwrap(space, w_obj)
    index = rgc.get_rpy_type_index(gcref)
    if index < 0:
        raise missing_operation(space)
    return space.wrap(index)

def _list_w_obj_referents(gcref, result_w):
    # Get all W_Root reachable directly from gcref, and add them to
    # the list 'result_w'.  The logic here is not robust against gc
    # moves, and may return the same object several times.
    seen = {}     # map {current_addr: obj}
    pending = [gcref]
    i = 0
    while i < len(pending):
        gcrefparent = pending[i]
        i += 1
        for gcref in rgc.get_rpy_referents(gcrefparent):
            key = rgc.cast_gcref_to_int(gcref)
            if gcref == seen.get(key, rgc.NULL_GCREF):
                continue     # already in 'seen'
            seen[key] = gcref
            w_obj = try_cast_gcref_to_w_root(gcref)
            if w_obj is not None:
                result_w.append(w_obj)
            else:
                pending.append(gcref)

def _get_objects_from_rpy(list_of_gcrefs):
    # given a list of gcrefs that may or may not be W_Roots, build a list
    # of W_Roots obtained by following references from there.
    result_w = []   # <- list of W_Roots
    for gcref in list_of_gcrefs:
        if gcref:
            w_obj = try_cast_gcref_to_w_root(gcref)
            if w_obj is not None:
                result_w.append(w_obj)
            else:
                _list_w_obj_referents(gcref, result_w)
    return result_w

def get_objects(space):
    """Return a list of all app-level objects."""
    roots = rgc.get_rpy_roots()
    pending_w = _get_objects_from_rpy(roots)
    # continue by following every W_Root.  Note that this will force a hash
    # on every W_Root, which is kind of bad, but not on every RPython object,
    # which is really good.
    result_w = {}
    while len(pending_w) > 0:
        previous_w = pending_w
        pending_w = []
        for w_obj in previous_w:
            if w_obj not in result_w:
                result_w[w_obj] = None
                gcref = rgc.cast_instance_to_gcref(w_obj)
                _list_w_obj_referents(gcref, pending_w)
    return space.newlist(result_w.keys())

def get_referents(space, args_w):
    """Return a list of objects directly referred to by any of the arguments.
    Approximative: follow references recursively until it finds
    app-level objects.  May return several times the same object, too."""
    result = []
    for w_obj in args_w:
        gcref = rgc.cast_instance_to_gcref(w_obj)
        _list_w_obj_referents(gcref, result)
    return space.newlist(result)

def get_referrers(space, args_w):
    """Return the list of objects that directly refer to any of objs."""
    roots = rgc.get_rpy_roots()
    pending_w = _get_objects_from_rpy(roots)
    arguments_w = {}
    for w_obj in args_w:
        arguments_w[w_obj] = None
    # continue by following every W_Root.  Same remark about hashes as
    # in get_objects().
    result_w = {}
    seen_w = {}
    while len(pending_w) > 0:
        previous_w = pending_w
        pending_w = []
        for w_obj in previous_w:
            if w_obj not in seen_w:
                seen_w[w_obj] = None
                gcref = rgc.cast_instance_to_gcref(w_obj)
                referents_w = []
                _list_w_obj_referents(gcref, referents_w)
                for w_subobj in referents_w:
                    if w_subobj in arguments_w:
                        result_w[w_obj] = None
                pending_w += referents_w
    return space.newlist(result_w.keys())

@unwrap_spec(fd=int)
def _dump_rpy_heap(space, fd):
    try:
        ok = rgc.dump_rpy_heap(fd)
    except OSError, e:
        raise wrap_oserror(space, e)
    if not ok:
        raise missing_operation(space)

def get_typeids_z(space):
    a = rgc.get_typeids_z()
    s = ''.join([a[i] for i in range(len(a))])
    return space.wrap(s)
