from pypy.rlib.objectmodel import we_are_translated
from pypy.lib.identity_dict import identity_dict


class State:
    def __init__(self, space):
        self.py_objects_w2r = identity_dict() # w_obj -> raw PyObject
        self.py_objects_r2w = {} # addr of raw PyObject -> w_obj
        self.exc_type = None
        self.exc_value = None

