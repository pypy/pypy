from pypy.rlib.objectmodel import we_are_translated
from pypy.lib.identity_dict import identity_dict


class State:
    def __init__(self, space):
        from pypy.module.cpyext import api
        self.py_objects_w2r = identity_dict() # w_obj -> raw PyObject
        self.py_objects_r2w = {} # addr of raw PyObject -> w_obj
        if not we_are_translated():
            self.api_lib = str(api.build_bridge(space))
        else:
            XXX # build an import library when translating pypy.

