class GcHooks(object):

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
