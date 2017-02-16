from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt
from rpython.rlib import rgc


@unwrap_spec(generation=int)
def collect(space, generation=0):
    "Run a full collection.  The optional argument is ignored."
    # First clear the method and the map cache.
    # See test_gc for an example of why.
    from pypy.objspace.std.typeobject import MethodCache
    from pypy.objspace.std.mapdict import MapAttrCache
    cache = space.fromcache(MethodCache)
    cache.clear()
    cache = space.fromcache(MapAttrCache)
    cache.clear()

    rgc.collect()

    # if we are running in gc.disable() mode but gc.collect() is called,
    # we should still call the finalizers now.  We do this as an attempt
    # to get closer to CPython's behavior: in Py3.5 some tests
    # specifically rely on that.  This is similar to how, in CPython, an
    # explicit gc.collect() will invoke finalizers from cycles and fully
    # ignore the gc.disable() mode.
    temp_reenable = not space.user_del_action.enabled_at_app_level
    if temp_reenable:
        enable_finalizers(space)
    try:
        # fetch the pending finalizers from the queue, where they are
        # likely to have been added by rgc.collect() above, and actually
        # run them now.  This forces them to run before this function
        # returns, and also always in the enable_finalizers() mode.
        space.user_del_action._run_finalizers()
    finally:
        if temp_reenable:
            disable_finalizers(space)

    return space.newint(0)

def enable(space):
    """Non-recursive version.  Enable finalizers now.
    If they were already enabled, no-op.
    If they were disabled even several times, enable them anyway.
    """
    if not space.user_del_action.enabled_at_app_level:
        space.user_del_action.enabled_at_app_level = True
        enable_finalizers(space)

def disable(space):
    """Non-recursive version.  Disable finalizers now.  Several calls
    to this function are ignored.
    """
    if space.user_del_action.enabled_at_app_level:
        space.user_del_action.enabled_at_app_level = False
        disable_finalizers(space)

def isenabled(space):
    return space.newbool(space.user_del_action.enabled_at_app_level)

def enable_finalizers(space):
    uda = space.user_del_action
    if uda.finalizers_lock_count == 0:
        raise oefmt(space.w_ValueError, "finalizers are already enabled")
    uda.finalizers_lock_count -= 1
    if uda.finalizers_lock_count == 0:
        pending = uda.pending_with_disabled_del
        uda.pending_with_disabled_del = None
        if pending is not None:
            for i in range(len(pending)):
                uda._call_finalizer(pending[i])
                pending[i] = None   # clear the list as we progress

def disable_finalizers(space):
    uda = space.user_del_action
    uda.finalizers_lock_count += 1
    if uda.pending_with_disabled_del is None:
        uda.pending_with_disabled_del = []

# ____________________________________________________________

@unwrap_spec(filename='str0')
def dump_heap_stats(space, filename):
    tb = rgc._heap_stats()
    if not tb:
        raise oefmt(space.w_RuntimeError, "Wrong GC")
    f = open(filename, mode="w")
    for i in range(len(tb)):
        f.write("%d %d " % (tb[i].count, tb[i].size))
        f.write(",".join([str(tb[i].links[j]) for j in range(len(tb))]) + "\n")
    f.close()
