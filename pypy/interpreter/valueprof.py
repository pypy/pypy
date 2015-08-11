from rpython.rlib import jit
from rpython.rlib.rweakref import ref, dead_ref

SEEN_NOTHING = '\x00'
SEEN_INT = '\x01'
SEEN_OBJ = '\x02'
SEEN_TOO_MUCH = '\x03'

class ValueProf(object):
    _immutable_fields_ = ['_vprof_status?']

    def __init__(self, msg=''):
        # only if you subclass normally
        self.init_valueprof(msg)

    def init_valueprof(self, msg=''):
        self._vprof_status = SEEN_NOTHING
        self._vprof_value_int = 0
        self._vprof_value_wref = dead_ref
        self._vprof_counter = 0
        self._vprof_msg = msg

    def is_int(self, w_obj):
        raise NotImplementedError("abstract base")

    def get_int_val(self, w_obj):
        raise NotImplementedError("abstract base")

    def see_write(self, w_value):
        if self.is_int(w_value):
            return self.see_int(self.get_int_val(w_value))
        return self.see_object(w_value)

    def see_int(self, value):
        status = self._vprof_status
        if status == SEEN_NOTHING:
            self._vprof_value_int = value
            self._vprof_status = SEEN_INT
        elif status == SEEN_INT:
            if self.read_constant_int() != value:
                if self._vprof_counter >= 200:
                    print "NO LONGER CONSTANT", self._vprof_msg, 'int', value
                self._vprof_status = SEEN_TOO_MUCH
            else:
                self._vprof_counter += 1
                if self._vprof_counter == 200:
                    print self._vprof_msg, 'int', value
        elif status == SEEN_OBJ:
            self._vprof_status = SEEN_TOO_MUCH
            if self._vprof_counter >= 200:
                print "NO LONGER CONSTANT", self._vprof_msg, 'int', value

    def see_object(self, value):
        status = self._vprof_status
        if value is None:
            if status != SEEN_TOO_MUCH:
                self._vprof_status = SEEN_TOO_MUCH
        elif status == SEEN_NOTHING:
            try:
                self._vprof_value_wref = ref(value)
                self._vprof_status = SEEN_OBJ
            except TypeError:
                # for tests, which really use unwrapped ints in a few places
                self._vprof_status = SEEN_TOO_MUCH
        elif status == SEEN_INT:
            if self._vprof_counter >= 200:
                print "NO LONGER CONSTANT", self._vprof_msg, 'obj', value
            self._vprof_status = SEEN_TOO_MUCH
        elif status == SEEN_OBJ:
            if self.try_read_constant_obj() is not value:
                if self._vprof_counter >= 200:
                    print "NO LONGER CONSTANT", self._vprof_msg, 'obj', value
                self._vprof_status = SEEN_TOO_MUCH
            else:
                self._vprof_counter += 1
                if self._vprof_counter == 200:
                    print self._vprof_msg, 'obj', value

    def can_fold_read_int(self):
        return self._vprof_status == SEEN_INT

    def can_fold_read_obj(self):
        return self._vprof_status == SEEN_OBJ

    @jit.elidable
    def read_constant_int(self):
        assert self.can_fold_read_int()
        return self._vprof_value_int

    @jit.elidable
    def try_read_constant_obj(self):
        assert self.can_fold_read_obj()
        return self._vprof_value_wref()


