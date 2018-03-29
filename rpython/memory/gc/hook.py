class GcHooks(object):

    def on_gc_minor(self, total_memory_used, pinned_objects):
        """
        Called after a minor collection
        """

    def on_gc_collect(self, count, arenas_count_before, arenas_count_after,
                      arenas_bytes, rawmalloc_bytes_before,
                      rawmalloc_bytes_after):
        """
        Called after a major collection is fully done
        """
