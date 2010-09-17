from pypy.rlib import rgc
from pypy.interpreter.baseobjspace import W_Root, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.error import wrap_oserror
from pypy.rlib.objectmodel import we_are_translated


class W_GcRef(Wrappable):
    def __init__(self, gcref):
        self.gcref = gcref

W_GcRef.typedef = TypeDef("GcRef")


def try_cast_gcref_to_w_root(gcref):
    w_obj = rgc.try_cast_gcref_to_instance(W_Root, gcref)
    if not we_are_translated() and not hasattr(w_obj, 'typedef'):
        w_obj = None
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

def get_rpy_roots(space):
    lst = rgc.get_rpy_roots()
    return space.newlist([wrap(space, gcref) for gcref in lst if gcref])

def get_rpy_referents(space, w_obj):
    """Return a list of all the referents, as reported by the GC.
    This is likely to contain a lot of GcRefs."""
    gcref = unwrap(space, w_obj)
    lst = rgc.get_rpy_referents(gcref)
    return space.newlist([wrap(space, gcref) for gcref in lst])

def get_rpy_memory_usage(space, w_obj):
    """Return the memory usage of just the given object or GcRef.
    This does not include the internal structures of the object."""
    gcref = unwrap(space, w_obj)
    size = rgc.get_rpy_memory_usage(gcref)
    return space.wrap(size)

def get_rpy_type_index(space, w_obj):
    """Return an integer identifying the RPython type of the given
    object or GcRef.  The number starts at 1; it is an index in the
    file typeids.txt produced at translation."""
    gcref = unwrap(space, w_obj)
    index = rgc.get_rpy_type_index(gcref)
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
get_referents.unwrap_spec = [ObjSpace, 'args_w']

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
get_referrers.unwrap_spec = [ObjSpace, 'args_w']

def dump_rpy_heap(space, fd):
    """Write a full dump of the objects in the heap to the given file
    descriptor.  Format for each object (each item is one machine word):

        [addr] [typeindex] [size] [addr1]..[addrn] [-1]

    where [addr] is the address of the object, [typeindex] and [size]
    are as get_rpy_type_index() and get_rpy_memory_usage() would return,
    and [addr1]..[addrn] are addresses of other objects that this object
    points to.  The full dump is a list of such objects, with a marker
    [0][0][0][-1] inserted after all GC roots, before all non-roots.
    """
    try:
        rgc.dump_rpy_heap(fd)
    except OSError, e:
        raise wrap_oserror(space, e)
dump_rpy_heap.unwrap_spec = [ObjSpace, int]
