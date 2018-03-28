class GcHooks(object):

    def on_gc_minor(self, total_memory_used, pinned_objects):
        """
        Called after a minor collection
        """
