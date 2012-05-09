from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.rlib import rgc
from pypy.rlib.streamio import open_file_as_stream

def collect(space):
    "Run a full collection."
    # First clear the method cache.  See test_gc for an example of why.
    if space.config.objspace.std.withmethodcache:
        from pypy.objspace.std.typeobject import MethodCache
        cache = space.fromcache(MethodCache)
        cache.clear()
        if space.config.objspace.std.withmapdict:
            from pypy.objspace.std.mapdict import IndexCache
            cache = space.fromcache(IndexCache)
            cache.clear()
    rgc.collect()
    return space.wrap(0)

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
    if space.user_del_action.finalizers_lock_count == 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("finalizers are already enabled"))
    space.user_del_action.finalizers_lock_count -= 1
    space.user_del_action.fire()

def disable_finalizers(space):
    space.user_del_action.finalizers_lock_count += 1

# ____________________________________________________________

@unwrap_spec(filename='str0')
def dump_heap_stats(space, filename):
    tb = rgc._heap_stats()
    if not tb:
        raise OperationError(space.w_RuntimeError,
                             space.wrap("Wrong GC"))
    f = open_file_as_stream(filename, mode="w")
    for i in range(len(tb)):
        f.write("%d %d " % (tb[i].count, tb[i].size))
        f.write(",".join([str(tb[i].links[j]) for j in range(len(tb))]) + "\n")
    f.close()
