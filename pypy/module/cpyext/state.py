from pypy.rlib.objectmodel import we_are_translated
from pypy.lib.identity_dict import identity_dict
from pypy.interpreter.error import OperationError

class State:
    def __init__(self, space):
        self.py_objects_w2r = identity_dict() # w_obj -> raw PyObject
        self.py_objects_r2w = {} # addr of raw PyObject -> w_obj
        self.exc_type = None
        self.exc_value = None

    def check_and_raise_exception(self):
        exc_value = self.exc_value
        exc_type = self.exc_type
        if exc_type is not None or exc_value is not None:
            self.exc_value = None
            self.exc_type = None
            op_err = OperationError(exc_type, exc_value)
            raise op_err

