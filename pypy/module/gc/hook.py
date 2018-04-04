from rpython.memory.gc.hook import GcHooks
from rpython.memory.gc import incminimark 
from rpython.rlib.nonconst import NonConstant
from rpython.rlib.rarithmetic import r_uint
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.executioncontext import AsyncAction

class LowLevelGcHooks(GcHooks):

    def __init__(self, space):
        self.space = space
        self.hooks = space.fromcache(AppLevelHooks)

    def is_gc_minor_enabled(self):
        return self.hooks.gc_minor_enabled

    def is_gc_collect_step_enabled(self):
        return self.hooks.gc_collect_step_enabled

    def is_gc_collect_enabled(self):
        return self.hooks.gc_collect_enabled

    def on_gc_minor(self, total_memory_used, pinned_objects):
        action = self.hooks.gc_minor
        action.total_memory_used = total_memory_used
        action.pinned_objects = pinned_objects
        action.fire()

    def on_gc_collect_step(self, oldstate, newstate):
        action = self.hooks.gc_collect_step
        action.oldstate = oldstate
        action.newstate = newstate
        action.fire()

    def on_gc_collect(self, count, arenas_count_before, arenas_count_after,
                      arenas_bytes, rawmalloc_bytes_before,
                      rawmalloc_bytes_after):
        action = self.hooks.gc_collect
        action.count = count
        action.arenas_count_before = arenas_count_before
        action.arenas_count_after = arenas_count_after
        action.arenas_bytes = arenas_bytes
        action.rawmalloc_bytes_before = rawmalloc_bytes_before
        action.rawmalloc_bytes_after = rawmalloc_bytes_after
        action.fire()


class AppLevelHooks(object):

    def __init__(self, space):
        self.space = space
        self.gc_minor_enabled = False
        self.gc_collect_step_enabled = False
        self.gc_collect_enabled = False
        self.gc_minor = GcMinorHookAction(space)
        self.gc_collect_step = GcCollectStepHookAction(space)
        self.gc_collect = GcCollectHookAction(space)

    def set_hooks(self, space, w_on_gc_minor, w_on_gc_collect_step,
                  w_on_gc_collect):
        self.gc_minor_enabled = not space.is_none(w_on_gc_minor)
        self.gc_minor.w_callable = w_on_gc_minor
        self.gc_minor.fix_annotation()
        #
        self.gc_collect_step_enabled = not space.is_none(w_on_gc_collect_step)
        self.gc_collect_step.w_callable = w_on_gc_collect_step
        self.gc_collect_step.fix_annotation()
        #
        self.gc_collect_enabled = not space.is_none(w_on_gc_collect)
        self.gc_collect.w_callable = w_on_gc_collect
        self.gc_collect.fix_annotation()


class GcMinorHookAction(AsyncAction):
    w_callable = None
    total_memory_used = 0
    pinned_objects = 0

    def fix_annotation(self):
        # the annotation of the class and its attributes must be completed
        # BEFORE we do the gc transform; this makes sure that everything is
        # annotated with the correct types
        if NonConstant(False):
            self.total_memory_used = NonConstant(r_uint(42))
            self.pinned_objects = NonConstant(-42)
            self.fire()

    def perform(self, ec, frame):
        w_stats = W_GcMinorStats(self.total_memory_used, self.pinned_objects)
        self.space.call_function(self.w_callable, w_stats)


class GcCollectStepHookAction(AsyncAction):
    w_callable = None
    oldstate = 0
    newstate = 0

    def fix_annotation(self):
        # the annotation of the class and its attributes must be completed
        # BEFORE we do the gc transform; this makes sure that everything is
        # annotated with the correct types
        if NonConstant(False):
            self.oldstate = NonConstant(-42)
            self.newstate = NonConstant(-42)
            self.fire()

    def perform(self, ec, frame):
        w_stats = W_GcCollectStepStats(self.oldstate, self.newstate)
        self.space.call_function(self.w_callable, w_stats)


class GcCollectHookAction(AsyncAction):
    w_callable = None
    count = 0
    arenas_count_before = 0
    arenas_count_after = 0
    arenas_bytes = 0
    rawmalloc_bytes_before = 0
    rawmalloc_bytes_after = 0

    def fix_annotation(self):
        # the annotation of the class and its attributes must be completed
        # BEFORE we do the gc transform; this makes sure that everything is
        # annotated with the correct types
        if NonConstant(False):
            self.count = NonConstant(-42)
            self.arenas_count_before = NonConstant(-42)
            self.arenas_count_after = NonConstant(-42)
            self.arenas_bytes = NonConstant(r_uint(42))
            self.rawmalloc_bytes_before = NonConstant(r_uint(42))
            self.rawmalloc_bytes_after = NonConstant(r_uint(42))
            self.fire()

    def perform(self, ec, frame):
        w_stats = W_GcCollectStats(self.count,
                                   self.arenas_count_before,
                                   self.arenas_count_after,
                                   self.arenas_bytes,
                                   self.rawmalloc_bytes_before,
                                   self.rawmalloc_bytes_after)
        self.space.call_function(self.w_callable, w_stats)


class W_GcMinorStats(W_Root):

    def __init__(self, total_memory_used, pinned_objects):
        self.total_memory_used = total_memory_used
        self.pinned_objects = pinned_objects


class W_GcCollectStepStats(W_Root):

    def __init__(self, oldstate, newstate):
        self.oldstate = oldstate
        self.newstate = newstate


class W_GcCollectStats(W_Root):
    def __init__(self, count, arenas_count_before, arenas_count_after,
                 arenas_bytes, rawmalloc_bytes_before,
                 rawmalloc_bytes_after):
        self.count = count
        self.arenas_count_before = arenas_count_before
        self.arenas_count_after = arenas_count_after
        self.arenas_bytes = arenas_bytes
        self.rawmalloc_bytes_before = rawmalloc_bytes_before
        self.rawmalloc_bytes_after = rawmalloc_bytes_after


# just a shortcut to make the typedefs shorter
def wrap_many_ints(cls, names):
    d = {}
    for name in names:
        d[name] = interp_attrproperty(name, cls=cls, wrapfn="newint")
    return d

W_GcMinorStats.typedef = TypeDef(
    "GcMinorStats",
    **wrap_many_ints(W_GcMinorStats, (
        "total_memory_used",
        "pinned_objects"))
    )

W_GcCollectStepStats.typedef = TypeDef(
    "GcCollectStepStats",
    STATE_SCANNING = incminimark.STATE_SCANNING,
    STATE_MARKING = incminimark.STATE_MARKING,
    STATE_SWEEPING = incminimark.STATE_SWEEPING,
    STATE_FINALIZING = incminimark.STATE_FINALIZING,
    GC_STATES = tuple(incminimark.GC_STATES),
    **wrap_many_ints(W_GcCollectStepStats, (
        "oldstate",
        "newstate"))
    )

W_GcCollectStats.typedef = TypeDef(
    "GcCollectStats",
    **wrap_many_ints(W_GcCollectStats, (
        "count",
        "arenas_count_before",
        "arenas_count_after",
        "arenas_bytes",
        "rawmalloc_bytes_before",
        "rawmalloc_bytes_after"))
    )


@unwrap_spec(w_on_gc_minor=WrappedDefault(None),
             w_on_gc_collect_step=WrappedDefault(None),
             w_on_gc_collect=WrappedDefault(None))
def set_hooks(space, w_on_gc_minor=None,
              w_on_gc_collect_step=None,
              w_on_gc_collect=None):
    hooks = space.fromcache(AppLevelHooks)
    hooks.set_hooks(space, w_on_gc_minor, w_on_gc_collect_step, w_on_gc_collect)
                                             
