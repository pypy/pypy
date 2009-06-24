
from pypy.interpreter import pycode, eval

class Code(pycode.PyCode):
    def __init__(self, space,  argcount, nlocals, stacksize, flags,
                     code, consts, names, varnames, filename,
                     name, firstlineno, lnotab, freevars, cellvars,
                     hidden_applevel=False, magic = pycode.default_magic):
        """Initialize a new code object from parameters given by
        the pypy compiler"""
        self.space = space
        eval.Code.__init__(self, name)
        self.co_argcount = argcount
        self.co_nlocals = nlocals
        self.co_stacksize = stacksize
        self.co_flags = flags
        self.co_code = code
        self.co_consts_w = consts
        self.co_names_w = [space.new_interned_str(aname) for aname in names]
        self.co_varnames = varnames
        self.co_freevars = freevars
        self.co_cellvars = cellvars
        self.co_filename = filename
        self.co_name = name
        self.co_firstlineno = firstlineno
        self.co_lnotab = lnotab
        self.hidden_applevel = hidden_applevel
        self.magic = magic
        #self._signature = cpython_code_signature(self)
        # Precompute what arguments need to be copied into cellvars
        self._args_as_cellvars = []
        
#         if self.co_cellvars:
#             argcount = self.co_argcount
#             assert argcount >= 0     # annotator hint
#             if self.co_flags & CO_VARARGS:
#                 argcount += 1
#             if self.co_flags & CO_VARKEYWORDS:
#                 argcount += 1
#             # Cell vars could shadow already-set arguments.
#             # astcompiler.pyassem used to be clever about the order of
#             # the variables in both co_varnames and co_cellvars, but
#             # it no longer is for the sake of simplicity.  Moreover
#             # code objects loaded from CPython don't necessarily follow
#             # an order, which could lead to strange bugs if .pyc files
#             # produced by CPython are loaded by PyPy.  Note that CPython
#             # contains the following bad-looking nested loops at *every*
#             # function call!
#             argvars  = self.co_varnames
#             cellvars = self.co_cellvars
#             for i in range(len(cellvars)):
#                 cellname = cellvars[i]
#                 for j in range(argcount):
#                     if cellname == argvars[j]:
#                         # argument j has the same name as the cell var i
#                         while len(self._args_as_cellvars) <= i:
#                             self._args_as_cellvars.append(-1)   # pad
#                         self._args_as_cellvars[i] = j

#         self._compute_flatcall()
