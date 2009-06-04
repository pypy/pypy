"""This is not the JIT :-)

This is transformed to become a JIT by code elsewhere: pypy/jit/*
"""
import py
import sys
from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import JitDriver, hint
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, Arguments
from pypy.interpreter.eval import Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.function import Function
from pypy.interpreter.pyopcode import ExitFrame

PyFrame._virtualizable2_ = True
PyFrame._always_virtual_ = ['valuestack_w', 'fastlocals_w']

class PyPyJitDriver(JitDriver):
    reds = ['frame', 'ec']
    greens = ['next_instr', 'pycode']
    virtualizables = ['frame']

##    def compute_invariants(self, reds, next_instr, pycode):
##        # compute the information that really only depends on next_instr
##        # and pycode
##        frame = reds.frame
##        valuestackdepth = frame.valuestackdepth
##        blockstack = frame.blockstack
##        return (valuestackdepth, blockstack)

pypyjitdriver = PyPyJitDriver()

class __extend__(PyFrame):

    def dispatch(self, pycode, next_instr, ec):
        next_instr = r_uint(next_instr)
        try:
            while True:
                pypyjitdriver.jit_merge_point(ec=ec,
                    frame=self, next_instr=next_instr, pycode=pycode)
                co_code = pycode.co_code
                self.valuestackdepth = hint(self.valuestackdepth, promote=True)
                next_instr = self.handle_bytecode(co_code, next_instr, ec)
        except ExitFrame:
            return self.popvalue()

    def JUMP_ABSOLUTE(f, jumpto, next_instr, ec=None):
        pypyjitdriver.can_enter_jit(frame=f, ec=ec, next_instr=jumpto,
                                    pycode=f.getcode())
        return jumpto

##class __extend__(Function):
##    __metaclass__ = extendabletype

##    def getcode(self):
##        # if the self is a compile time constant and if its code
##        # is a BuiltinCode => grab and return its code as a constant
##        if _is_early_constant(self):
##            from pypy.interpreter.gateway import BuiltinCode
##            code = hint(self, deepfreeze=True).code
##            if not isinstance(code, BuiltinCode): code = self.code
##        else:
##            code = self.code
##        return code
        

# ____________________________________________________________
#
# Public interface    

def set_param(space, args):
    '''Configure the tunable JIT parameters.
        * set_param(name=value, ...)            # as keyword arguments
        * set_param("name=value,name=value")    # as a user-supplied string
    '''
    args_w, kwds_w = args.unpack()
    if len(args_w) > 1:
        msg = ("set_param() takes at most 1 non-keyword argument, %d given"
               % len(args_w))
        raise OperationError(space.w_TypeError, space.wrap(msg))
    if len(args_w) == 1:
        text = space.str_w(args_w[0])
        try:
            pypyjitdriver.set_user_param(text)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("error in JIT parameters string"))
    for key, w_value in kwds_w.items():
        intval = space.int_w(w_value)
        try:
            pypyjitdriver.set_param(key, intval)
        except ValueError:
            raise OperationError(space.w_TypeError,
                                 space.wrap("no JIT parameter '%s'" % (key,)))

set_param.unwrap_spec = [ObjSpace, Arguments]
