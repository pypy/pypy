

class StmGCSharedArea(object):

    def __init__(self, gc, page_size, arena_size, small_request_threshold):
        ...
        # The ArenaCollection() handles the nonmovable objects allocation.
        # It contains all small GCFLAG_GLOBAL objects.  The non-small ones
        # are directly malloc'ed.
        if ArenaCollectionClass is None:
            from pypy.rpython.memory.gc import minimarkpage
            ArenaCollectionClass = minimarkpage.ArenaCollection
        self.ac = ArenaCollectionClass(arena_size, page_size,
                                       small_request_threshold)
