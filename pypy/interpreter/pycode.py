"""
PyCode class implementation.

This class is similar to the built-in code objects.
It avoids wrapping existing code object, instead,
it plays its role without exposing real code objects.
SInce in C Python the only way to crate a code object
by somehow call into the builtin compile, we implement
the creation of our code object by defining out own compile,
wich ()at the moment) calls back into the real compile,
hijacks the code object and creates our code object from that.
compile is found in the builtin.py file.
"""

# XXX todo:
# look at this if it makes sense
# think of a proper base class???

import baseobjspace
from appfile import AppFile

# no appfile neede, yet
#appfile = AppFile(__name__, ["interpreter"])

class PyBaseCode:
    def __init__(self):
        self.co_filename = ""
        self.co_name = ""
        
class PyByteCode(PyBaseCode):
    """Represents a code object for Python functions.

    Public fields:
    to be done
    """

    def __init__(self):
        """ initialize all attributes to just something. """
        self.co_argcount = 0
        self.co_nlocals = 0
        self.co_stacksize = 0
        self.co_flags = 0
        self.co_code = None
        self.co_consts = None
        self.co_names = None
        self.co_varnames = None
        self.co_freevars = None
        self.co_cellvars = None
        # The rest doesn't count for hash/cmp
        self.co_firstlineno = 0 #first source line number
        self.co_lnotab = "" # string (encoding addr<->lineno mapping)
        
    ### codeobject initialization ###

    def _from_code(self, code):
        """ Initialize the code object from a real one.
            This is just a hack, until we have our own compile.
            At the moment, we just fake this.
            This method is called by our compile builtin function.
        """
        import types
        assert(type(code is types.CodeType))
        # simply try to suck in all attributes we know of
        for name in self.__dict__.keys():
            value = getattr(code, name)
            setattr(self, name, value)

    def eval_code(self, space, w_globals, w_locals):
        frame = pypy.interpreter.pyframe.PyFrame(space, self,
                                             w_globals, w_locals)
        ec = space.getexecutioncontext()
        w_ret = ec.eval_frame(frame)
        return w_ret
    
