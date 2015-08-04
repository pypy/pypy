from rpython.rlib import jit
from rpython.rlib.rweakref import ref, dead_ref

class ValueProf(object):
    def __init__(self, size, threshold=200):
        self.values = [dead_ref] * size
        self.values_int = [-1] * size
        self.counters = [0] * size
        self.threshold = 200
        self.frozen = False

    @jit.elidable
    def freeze(self):
        # this works because we only ever change it in one direction
        self.frozen = True

    def see_int(self, index, value):
        if self.frozen:
            return
        if self.counters[index] < 0 and self.values_int[index] == value:
            self.counters[index] -= 1
            return -self.counters[index]
        else:
            self.values_int[index] = value
            self.counters[index] = -1
            self.values[index] = dead_ref
            return 1

    def see_object(self, index, value):
        if self.frozen:
            return
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

    @jit.elidable
    def is_variable_constant(self, index):
        assert self.frozen
        counter = self.counters[index]
        if counter > 0:
            return counter > self.threshold
        else:
            return -counter > self.threshold

    @jit.elidable
    def is_variable_int(self, index):
        assert self.frozen
        assert self.is_variable_constant(index)
        return self.counters[index] < 0

    @jit.elidable
    def variable_value_int(self, index):
        assert self.is_variable_int(index)
        return self.values_int[index]

    @jit.elidable
    def variable_value_object(self, index):
        assert self.is_variable_constant(index) and not self.is_variable_int(index)
        return self.values[index]
