from rpython.rlib import rgc

class GcHooks(object):
    """
    Base class to write your own GC hooks.

    Subclasses are expected to override the on_* methods. Note that such
    methods can do only simple stuff such as updating statistics and/or
    setting a flag: in particular, they cannot do anything which can possibly
    trigger a GC collection.
    """

    def __init__(self):
        self.gc_minor_enabled = False
        self.gc_collect_step_enabled = False
        self.gc_collect_enabled = False

    def on_gc_minor(self, total_memory_used, pinned_objects):
        """
        Called after a minor collection
        """

    def on_gc_collect_step(self, oldstate, newstate):
        """
        Called after each individual step of a major collection, in case the GC is
        incremental.

        ``oldstate`` and ``newstate`` are integers which indicate the GC
        state; for incminimark, see incminimark.STATE_* and
        incminimark.GC_STATES.
        """


    def on_gc_collect(self, count, arenas_count_before, arenas_count_after,
                      arenas_bytes, rawmalloc_bytes_before,
                      rawmalloc_bytes_after):
        """
        Called after a major collection is fully done
        """

    # the fire_* methods are meant to be called from the GC are should NOT be
    # overridden

    @rgc.no_collect
    def fire_gc_minor(self, total_memory_used, pinned_objects):
        if self.gc_minor_enabled:
            self.on_gc_minor(total_memory_used, pinned_objects)

    @rgc.no_collect
    def fire_gc_collect_step(self, oldstate, newstate):
        if self.gc_collect_step_enabled:
            self.on_gc_collect_step(oldstate, newstate)

    @rgc.no_collect
    def fire_gc_collect(self, count, arenas_count_before, arenas_count_after,
                        arenas_bytes, rawmalloc_bytes_before,
                        rawmalloc_bytes_after):
        if self.gc_collect_enabled:
            self.on_gc_collect(count, arenas_count_before, arenas_count_after,
                               arenas_bytes, rawmalloc_bytes_before,
                               rawmalloc_bytes_after)
