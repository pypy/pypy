from rpython.rlib import rgc
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt, wrap_oserror
from rpython.rlib.objectmodel import we_are_translated


class W_GcRef(W_Root):
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
    if isinstance(w_obj, W_GcRef):
        gcref = w_obj.gcref
    else:
        gcref = rgc.cast_instance_to_gcref(w_obj)
    return gcref

def missing_operation(space):
    return oefmt(space.w_NotImplementedError,
                 "operation not implemented by this GC")


# ____________________________________________________________

class PathEntry(object):
    # PathEntries are nodes of a complete tree of all objects, but
    # built lazily (there is only one branch alive at any time).
    # Each node has a 'gcref' and the list of referents from this gcref.
    def __init__(self, prev, gcref, referents):
        self.prev = prev
        self.gcref = gcref
        self.referents = referents
        self.remaining = len(referents)

    def get_most_recent_w_obj(self):
        entry = self
        while entry is not None:
            if entry.gcref:
                w_obj = try_cast_gcref_to_w_root(entry.gcref)
                if w_obj is not None:
                    return w_obj
            entry = entry.prev
        return None

def do_get_referrers(w_arg):
    result_w = []
    gcarg = rgc.cast_instance_to_gcref(w_arg)
    roots = [gcref for gcref in rgc.get_rpy_roots() if gcref]
    head = PathEntry(None, rgc.NULL_GCREF, roots)
    while True:
        head.remaining -= 1
        if head.remaining >= 0:
            gcref = head.referents[head.remaining]
            if not rgc.get_gcflag_extra(gcref):
                # not visited so far
                if gcref == gcarg:
                    w_obj = head.get_most_recent_w_obj()
                    if w_obj is not None:
                        result_w.append(w_obj)   # found!
                        rgc.toggle_gcflag_extra(gcref)  # toggle twice
                rgc.toggle_gcflag_extra(gcref)
                head = PathEntry(head, gcref, rgc.get_rpy_referents(gcref))
        else:
            # no more referents to visit
            head = head.prev
            if head is None:
                break
    # done.  Clear flags carefully
    rgc.toggle_gcflag_extra(gcarg)
    rgc.clear_gcflag_extra(roots)
    rgc.clear_gcflag_extra([gcarg])
    return result_w

# ____________________________________________________________

def _list_w_obj_referents(gcref, result_w):
    # Get all W_Root reachable directly from gcref, and add them to
    # the list 'result_w'.
    pending = []    # = list of all objects whose gcflag was toggled
    i = 0
    gcrefparent = gcref
    while True:
        for gcref in rgc.get_rpy_referents(gcrefparent):
            if rgc.get_gcflag_extra(gcref):
                continue
            rgc.toggle_gcflag_extra(gcref)
            pending.append(gcref)

        while i < len(pending):
            gcrefparent = pending[i]
            i += 1
            w_obj = try_cast_gcref_to_w_root(gcrefparent)
            if w_obj is not None:
                result_w.append(w_obj)
            else:
                break   # jump back to the start of the outermost loop
        else:
            break   # done

    for gcref in pending:
        rgc.toggle_gcflag_extra(gcref)    # reset the gcflag_extra's

# ____________________________________________________________

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

def get_objects(space):
    """Return a list of all app-level objects."""
    if not rgc.has_gcflag_extra():
        raise missing_operation(space)
    result_w = rgc.do_get_objects(try_cast_gcref_to_w_root)
    return space.newlist(result_w)

def get_referents(space, args_w):
    """Return a list of objects directly referred to by any of the arguments.
    """
    if not rgc.has_gcflag_extra():
        raise missing_operation(space)
    result_w = []
    for w_obj in args_w:
        gcref = rgc.cast_instance_to_gcref(w_obj)
        _list_w_obj_referents(gcref, result_w)
    rgc.assert_no_more_gcflags()
    return space.newlist(result_w)

def get_referrers(space, args_w):
    """Return the list of objects that directly refer to any of objs."""
    if not rgc.has_gcflag_extra():
        raise missing_operation(space)
    result_w = []
    for w_arg in args_w:
        result_w += do_get_referrers(w_arg)
    rgc.assert_no_more_gcflags()
    return space.newlist(result_w)

@unwrap_spec(fd=int)
def _dump_rpy_heap(space, fd):
    try:
        ok = rgc.dump_rpy_heap(fd)
    except OSError as e:
        raise wrap_oserror(space, e)
    if not ok:
        raise missing_operation(space)

def get_typeids_z(space):
    a = rgc.get_typeids_z()
    s = ''.join([a[i] for i in range(len(a))])
    return space.wrap(s)

def get_typeids_list(space):
    l = rgc.get_typeids_list()
    list_w = [space.wrap(l[i]) for i in range(len(l))]
    return space.newlist(list_w)
