"""This is not the JIT :-)

The pypyjit module helpers set the 'jit_enable' flag on code objects.
The code below makes two identical copies of the interpreter's main
loop, and the flag controls which of them is used.  One of them
(dispatch_jit) is transformed to become a JIT by code elsewhere:
pypy/jit/*
"""
import py
import sys
from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import hint, _is_early_constant
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.eval import Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.function import Function
from pypy.interpreter.pyopcode import Return, Yield


Frame._virtualizable_ = True
PyCode.jit_enable = False     # new default attribute
super_dispatch = PyFrame.dispatch

class __extend__(PyFrame):

    def dispatch(self, pycode, next_instr, ec):
        if pycode.jit_enable:
            return self.dispatch_jit(pycode, next_instr, ec)
        else:
            self = hint(self, access_directly=True)
            return super_dispatch(self, pycode, next_instr, ec)
            
    def dispatch_jit(self, pycode, next_instr, ec):
        hint(None, global_merge_point=True)
        pycode = hint(pycode, deepfreeze=True)

        entry_fastlocals_w = self.jit_enter_frame(pycode, next_instr)

        # For the sequel, force 'next_instr' to be unsigned for performance
        next_instr = r_uint(next_instr)
        co_code = pycode.co_code

        try:
            try:
                while True:
                    hint(None, global_merge_point=True)
                    next_instr = self.handle_bytecode(co_code, next_instr, ec)
            except Return:
                w_result = self.popvalue()
                self.blockstack = None
                self.valuestack_w = None
                return w_result
            except Yield:
                w_result = self.popvalue()
                return w_result
        finally:
            self.jit_leave_frame(pycode, entry_fastlocals_w)

    def jit_enter_frame(self, pycode, next_instr):
        # *loads* of nonsense for now

        fastlocals_w = [None] * pycode.co_nlocals

        if next_instr == 0:
            # first time we enter this function
            depth = 0
            self.blockstack = []

            numargs = pycode.co_argcount
            if pycode.co_flags & CO_VARARGS:     numargs += 1
            if pycode.co_flags & CO_VARKEYWORDS: numargs += 1
            while True:
                numargs -= 1
                if numargs < 0:
                    break
                hint(numargs, concrete=True)
                w_obj = self.fastlocals_w[numargs]
                assert w_obj is not None
                fastlocals_w[numargs] = w_obj

        else:
            stuff = self.valuestackdepth
            if len(self.blockstack):
                stuff |= (-sys.maxint-1)

            stuff = hint(stuff, promote=True)
            if stuff >= 0:
                # blockdepth == 0, common case
                self.blockstack = []
            depth = stuff & sys.maxint

            i = pycode.co_nlocals
            while True:
                i -= 1
                if i < 0:
                    break
                hint(i, concrete=True)
                w_obj = self.fastlocals_w[i]
                fastlocals_w[i] = w_obj

        self.pycode = pycode
        self.valuestackdepth = depth

        entry_fastlocals_w = self.fastlocals_w
        self.fastlocals_w = fastlocals_w

        virtualstack_w = [None] * pycode.co_stacksize
        while depth > 0:
            depth -= 1
            hint(depth, concrete=True)
            virtualstack_w[depth] = self.valuestack_w[depth]
        self.valuestack_w = virtualstack_w
        return entry_fastlocals_w

    def jit_leave_frame(self, pycode, entry_fastlocals_w):
        i = pycode.co_nlocals
        while True:
            i -= 1
            if i < 0:
                break
            hint(i, concrete=True)
            entry_fastlocals_w[i] = self.fastlocals_w[i]

        self.fastlocals_w = entry_fastlocals_w


PORTAL = PyFrame.dispatch_jit

class __extend__(Function):
    __metaclass__ = extendabletype

    def getcode(self):
        # if the self is a compile time constant and if its code
        # is a BuiltinCode => grab and return its code as a constant
        if _is_early_constant(self):
            from pypy.interpreter.gateway import BuiltinCode
            code = hint(self, deepfreeze=True).code
            if not isinstance(code, BuiltinCode): code = self.code
        else:
            code = self.code
        return code
        

# ____________________________________________________________
#
# Public interface

def enable(space, w_code, w_enabled=True):
    # save the app-level sys.executable in JITInfo, where the machine
    # code backend can fish for it - XXX the following import will look
    # less obscure once codebuf.py is moved to a general
    # processor-independent place
    from pypy.jit.codegen.hlinfo import highleveljitinfo
    if highleveljitinfo.sys_executable is None:
        highleveljitinfo.sys_executable = space.str_w(
            space.sys.get('executable'))

    code = space.interp_w(PyCode, w_code)
    code.jit_enable = space.is_true(w_enabled)
