from rpython.rlib.rweakref import ref, dead_ref

class ValueProf(object):
    def __init__(self, size):
        self.values = [dead_ref] * size
        self.values_int = [-1] * size
        self.counters = [0] * size

    def see_int(self, index, value):
        if self.counters[index] < 0 and self.values_int[index] == value:
            self.counters[index] -= 1
            return -self.counters[index]
        else:
            self.values_int[index] = value
            self.counters[index] = -1
            self.values[index] = dead_ref
            return 1

    def see_object(self, index, value):
        if value is None:
            self.values[index] = dead_ref
            self.counters[index] = 0
            return 0
        if self.values[index]() is value:
            assert self.counters[index] > 0
            self.counters[index] += 1
            return self.counters[index]
        else:
            self.values[index] = ref(value)
            self.counters[index] = 1
            self.values_int[index] = -1
            return 1
