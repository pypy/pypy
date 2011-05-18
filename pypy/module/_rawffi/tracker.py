
""" The file that keeps track about freed/kept-alive objects allocated
by _rawffi. Used for debugging ctypes
"""

class Tracker(object):
    DO_TRACING = True

    def __init__(self):
        self.alloced = {}

    def trace_allocation(self, address, obj):
        self.alloced[address] = None

    def trace_free(self, address):
        if address in self.alloced:
            del self.alloced[address]

# single, global, static object to keep all tracker info
tracker = Tracker()

def num_of_allocated_objects(space):
    return space.wrap(len(tracker.alloced))

def print_alloced_objects(space):
    xxx
    # eventually inspect and print what's left from applevel
