from rpython.rlib import jit
from rpython.rlib.rweakref import ref, dead_ref

SEEN_NOTHING = '\x00'
SEEN_INT = '\x01'
SEEN_OBJ = '\x02'
SEEN_TOO_MUCH = '\x03'

class ValueProf(object):
    _mixin_ = True
    _immutable_fields_ = ['status?']

    def __init__(self):
        # only if you subclass normally
        self.init_valueprof()

    def init_valueprof(self):
        self.status = SEEN_NOTHING
        self.value_int = 0
        self.value_wref = dead_ref

    def is_int(self, w_obj):
        raise NotImplementedError("abstract base")

    def get_int_val(self, w_obj):
        raise NotImplementedError("abstract base")

    def see_write(self, w_value):
        if self.is_int(w_value):
            return self.see_int(self.get_int_val(w_value))
        return self.see_object(w_value)

    def see_int(self, value):
        status = self.status
        if status == SEEN_NOTHING:
            self.value_int = value
            self.status = SEEN_INT
        elif status == SEEN_INT:
            if self.read_constant_int() != value:
                self.status = SEEN_TOO_MUCH
        elif status == SEEN_OBJ:
            self.status = SEEN_TOO_MUCH

    def see_object(self, value):
        status = self.status
        if value is None:
            if status != SEEN_TOO_MUCH:
                self.status = SEEN_TOO_MUCH
        elif status == SEEN_NOTHING:
            self.value_wref = ref(value)
            self.status = SEEN_OBJ
        elif status == SEEN_INT:
            self.status = SEEN_TOO_MUCH
        elif status == SEEN_OBJ:
            if self.try_read_constant_obj() is not value:
                self.status = SEEN_TOO_MUCH

    def can_fold_read_int(self):
        return self.status == SEEN_INT

    def can_fold_read_obj(self):
        return self.status == SEEN_OBJ

    @jit.elidable
    def read_constant_int(self):
        assert self.can_fold_read_int()
        return self.value_int

    @jit.elidable
    def try_read_constant_obj(self):
        assert self.can_fold_read_obj()
        return self.value_wref()


