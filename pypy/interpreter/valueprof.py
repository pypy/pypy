from rpython.rlib import jit, objectmodel
from rpython.rlib.rweakref import ref, dead_ref

SEEN_NOTHING = '0'
SEEN_CONSTANT_INT = 'i'
SEEN_CONSTANT_OBJ = 'o'
SEEN_CONSTANT_CLASS = 'c'
SEEN_TOO_MUCH = '?'

class ValueProf(object):
    _immutable_fields_ = ['_vprof_status?']

    def __init__(self, msg=''):
        # only if you subclass normally
        self.init_valueprof(msg)

    def init_valueprof(self, msg=''):
        self._vprof_status = SEEN_NOTHING
        self._vprof_value_int = 0
        self._vprof_value_wref = dead_ref
        self._vprof_const_cls = None
        self._vprof_counter = 0
        self._vprof_msg = msg

    def is_int(self, w_obj):
        raise NotImplementedError("abstract base")

    def get_int_val(self, w_obj):
        raise NotImplementedError("abstract base")

    def write_necessary(self, w_value):
        status = self._vprof_status
        if status == SEEN_TOO_MUCH:
            return True
        # we must have seen something already, because it only makes sense to
        # call write_necessary if there is already a value there
        assert not status == SEEN_NOTHING
        if status == SEEN_CONSTANT_INT:
            return (self.is_int(w_value) and
                self.read_constant_int() != self.get_int_val(w_value))
        elif status == SEEN_CONSTANT_OBJ:
            prev_obj = self.try_read_constant_obj()
            return prev_obj is not w_value
        return True


    def see_write(self, w_value):
        """ inform the value profiler of a write. returns False, unless the
        value is known to be a constant, and w_value that constant (in that
        case the caller can elide the write to the actual object, if that
        object already stores a value). """
        status = self._vprof_status
        if status == SEEN_TOO_MUCH:
            return False

        if w_value is None:
            self._vprof_status = SEEN_TOO_MUCH
            return False

        if status == SEEN_NOTHING:
            if self.is_int(w_value):
                self._vprof_value_int = self.get_int_val(w_value)
                self._vprof_status = SEEN_CONSTANT_INT
            else:
                try:
                    self._vprof_value_wref = ref(w_value)
                except TypeError:
                    # for tests, which really use unwrapped ints in a few places
                    self._vprof_status = SEEN_TOO_MUCH
                else:
                    self._vprof_const_cls = w_value.__class__
                    self._vprof_status = SEEN_CONSTANT_OBJ
        elif status == SEEN_CONSTANT_INT:
            if self.is_int(w_value):
                if self.read_constant_int() != self.get_int_val(w_value):
                    self._vprof_status = SEEN_CONSTANT_CLASS
                    self._vprof_const_cls = w_value.__class__
                else:
                    return True
            else:
                self._vprof_status = SEEN_TOO_MUCH
        elif status == SEEN_CONSTANT_OBJ:
            prev_obj = self.try_read_constant_obj()
            if prev_obj is not w_value:
                prev_cls = self.read_constant_cls()
                if prev_cls is w_value.__class__:
                    self._vprof_const_cls = prev_cls
                    self._vprof_status = SEEN_CONSTANT_CLASS
                else:
                    self._vprof_status = SEEN_TOO_MUCH
            else:
                return True
        elif status == SEEN_CONSTANT_CLASS:
            cls = self.read_constant_cls()
            if cls is not w_value.__class__:
                self._vprof_status = SEEN_TOO_MUCH
        return False

    def can_fold_read_int(self):
        return self._vprof_status == SEEN_CONSTANT_INT

    def can_fold_read_obj(self):
        return self._vprof_status == SEEN_CONSTANT_OBJ

    def class_is_known(self):
        return self._vprof_status == SEEN_CONSTANT_CLASS

    @jit.elidable
    def read_constant_int(self):
        assert self.can_fold_read_int()
        return self._vprof_value_int

    @jit.elidable
    def try_read_constant_obj(self):
        assert self.can_fold_read_obj()
        return self._vprof_value_wref()

    @jit.elidable
    def read_constant_cls(self):
        return self._vprof_const_cls

