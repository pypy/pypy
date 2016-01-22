from rpython.rlib import jit, objectmodel
from rpython.rlib.rweakref import ref, dead_ref

SEEN_NOTHING = '0'
SEEN_CONSTANT_INT = 'i'
SEEN_CONSTANT_OBJ = 'o'
SEEN_CONSTANT_CLASS = 'c'
SEEN_TOO_MUCH = '?'

class HeapProf(object):
    """ Some reusal heap profiling infrastructure. Can be used either as a base
    class, or as a mixin.

    The idea of this class is to have one HeapProf instance for many heap
    storage cells that are likely to store the same content. An example is
    having a HeapProf per field of a specific class. """

    _immutable_fields_ = ['_hprof_status?']

    def __init__(self, msg=''):
        # only if you subclass normally
        self.init_heapprof(msg)


    # ________________________________________________________________________
    # abstract methods that need to be overridden:

    def is_int(self, w_obj):
        """ returns whether the argument is a boxed integer. """
        raise NotImplementedError("abstract base")

    def get_int_val(self, w_obj):
        """ w_obj must be a boxed integer. returns the unboxed value of that
        integer. """
        raise NotImplementedError("abstract base")


    # ________________________________________________________________________
    # public interface

    def init_heapprof(self, msg=''):
        """ initialize the profiler. must be called if HeapProf is used as a
        mixin upon construction. """
        self._hprof_status = SEEN_NOTHING
        self._hprof_value_int = 0
        self._hprof_value_wref = dead_ref
        self._hprof_const_cls = None
        self._hprof_counter = 0
        self._hprof_msg = msg

    def see_write(self, w_value):
        """ inform the value profiler of a write."""
        status = self._hprof_status
        if status == SEEN_TOO_MUCH:
            return

        if w_value is None:
            self._hprof_status = SEEN_TOO_MUCH
            return

        if status == SEEN_NOTHING:
            if self.is_int(w_value):
                self._hprof_value_int = self.get_int_val(w_value)
                self._hprof_status = SEEN_CONSTANT_INT
            else:
                try:
                    self._hprof_value_wref = ref(w_value)
                except TypeError:
                    # for tests, which really use unwrapped ints in a few places
                    self._hprof_status = SEEN_TOO_MUCH
                else:
                    self._hprof_const_cls = w_value.__class__
                    self._hprof_status = SEEN_CONSTANT_OBJ
        elif status == SEEN_CONSTANT_INT:
            if self.is_int(w_value):
                if self.read_constant_int() != self.get_int_val(w_value):
                    self._hprof_status = SEEN_CONSTANT_CLASS
                    self._hprof_const_cls = w_value.__class__
                else:
                    return
            else:
                self._hprof_status = SEEN_TOO_MUCH
        elif status == SEEN_CONSTANT_OBJ:
            prev_obj = self.try_read_constant_obj()
            if prev_obj is not w_value:
                prev_cls = self.read_constant_cls()
                if prev_cls is w_value.__class__:
                    self._hprof_const_cls = prev_cls
                    self._hprof_status = SEEN_CONSTANT_CLASS
                else:
                    self._hprof_status = SEEN_TOO_MUCH
            else:
                return
        elif status == SEEN_CONSTANT_CLASS:
            cls = self.read_constant_cls()
            if cls is not w_value.__class__:
                self._hprof_status = SEEN_TOO_MUCH
        return

    def write_necessary(self, w_value):
        """ for an already initialized object check whether writing w_value
        into the object is necessary. it is unnecessary if the profiler knows
        the value is a constant and that constant is equal to w_value. """
        status = self._hprof_status
        if status == SEEN_TOO_MUCH:
            return True
        # we must have seen something already, because it only makes sense to
        # call write_necessary if there is already a value there
        assert not status == SEEN_NOTHING
        if status == SEEN_CONSTANT_INT:
            if not self.is_int(w_value):
                return True
            return self.read_constant_int() != self.get_int_val(w_value)
        elif status == SEEN_CONSTANT_OBJ:
            prev_obj = self.try_read_constant_obj()
            return prev_obj is not w_value
        return True

    def can_fold_read_int(self):
        """ returns True if the heap profiler knows that the object stores a
        constant integer. """
        return self._hprof_status == SEEN_CONSTANT_INT

    def can_fold_read_obj(self):
        """ returns True if the heap profiler knows that the object stores a
        constant non-integer object. """
        return self._hprof_status == SEEN_CONSTANT_OBJ

    def class_is_known(self):
        """ returns True if the heap profiler knows the class of the stored
        object. """
        return self._hprof_status == SEEN_CONSTANT_CLASS

    @jit.elidable
    def read_constant_int(self):
        """ returns the stored constant integer value in unboxed form. this
        must only be called directly after having called
        self.can_fold_read_int() and that returned True. """
        assert self.can_fold_read_int()
        return self._hprof_value_int

    @jit.elidable
    def try_read_constant_obj(self):
        """ tries to return the stored constant object. this must only be
        called directly after having called self.can_fold_read_obj() and that
        returned True. The method may still return False, if the constant
        object was garbage collected in the meantime."""
        assert self.can_fold_read_obj()
        return self._hprof_value_wref()

    @jit.elidable
    def read_constant_cls(self):
        """ returns the class of the stored object. this must only be called
        directly after having called self.class_is_known() and that returned
        True. The returned class is typically used with
        jit.record_exact_class(..., class)"""
        return self._hprof_const_cls

