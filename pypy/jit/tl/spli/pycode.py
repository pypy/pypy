from pypy.interpreter import pycode
from pypy.jit.tl.spli import objects


class Code(objects.SPLIObject):

    def __init__(self, argcount, nlocals, stacksize, code, consts, names):
        """Initialize a new code object from parameters given by
        the pypy compiler"""
        self.co_argcount = argcount
        self.co_nlocals = nlocals
        self.co_stacksize = stacksize
        self.co_code = code
        self.co_consts_w = consts
        self.co_names = names

    @classmethod
    def _from_code(cls, space, code, hidden_applevel=False, code_hook=None):
        pyco = pycode.PyCode._from_code(space, code, code_hook=cls._from_code)
        return cls(pyco.co_argcount, pyco.co_nlocals, pyco.co_stacksize,
                   pyco.co_code, pyco.co_consts_w,
                   [name.as_str() for name in pyco.co_names_w])
