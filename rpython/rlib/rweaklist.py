import weakref
from rpython.rlib.rweakref import dead_ref


def _reduced_value(s):
    while True:
        divide = s & 1
        s >>= 1
        if not divide:
            return s


class RWeakListMixin(object):
    _mixin_ = True

    def initialize(self):
        self.handles = []
        self.look_distance = 0

    def get_all_handles(self):
        return self.handles

    def reserve_next_handle_index(self):
        # The reservation ordering done here is tweaked for pypy's
        # memory allocator.  We look from index 'look_distance'.
        # Look_distance increases from 0.  But we also look at
        # "look_distance/2" or "/4" or "/8", etc.  If we find that one
        # of these secondary locations is free, we assume it's because
        # there was recently a minor collection; so we reset
        # look_distance to 0 and start again from the lowest locations.
        length = len(self.handles)
        for d in range(self.look_distance, length):
            if self.handles[d]() is None:
                self.look_distance = d + 1
                return d
            s = _reduced_value(d)
            if self.handles[s]() is None:
                break
        # restart from the beginning
        for d in range(0, length):
            if self.handles[d]() is None:
                self.look_distance = d + 1
                return d
        # full! extend, but don't use '+=' here
        self.handles = self.handles + [dead_ref] * (length // 3 + 5)
        self.look_distance = length + 1
        return length

    def add_handle(self, content):
        index = self.reserve_next_handle_index()
        self.store_handle(index, content)
        return index

    def store_handle(self, index, content):
        self.handles[index] = weakref.ref(content)

    def fetch_handle(self, index):
        if 0 <= index < len(self.handles):
            return self.handles[index]()
        return None
