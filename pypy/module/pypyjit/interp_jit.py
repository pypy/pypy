"""This is not the JIT :-)

This is transformed to become a JIT by code elsewhere: pypy/jit/*
"""
import py
import sys
from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import JitDriver, hint, we_are_jitted
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import ObjSpace, Arguments
from pypy.interpreter.eval import Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.function import Function
from pypy.interpreter.pyopcode import ExitFrame
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.tool.stdlib_opcode import opcodedesc, HAVE_ARGUMENT
from opcode import opmap
from pypy.rlib.objectmodel import we_are_translated

PyFrame._virtualizable2_ = ['last_instr',
                            'valuestackdepth', 'valuestack_w[*]',
                            'fastlocals_w[*]',
                            ]

JUMP_ABSOLUTE = opmap['JUMP_ABSOLUTE']

def can_inline(next_instr, bytecode):
    if we_are_translated():
        bytecode = cast_base_ptr_to_instance(PyCode, bytecode)
    co_code = bytecode.co_code
    next_instr = 0
    while next_instr < len(co_code):
        opcode = ord(co_code[next_instr])
        next_instr += 1
        if opcode >= HAVE_ARGUMENT:
            next_instr += 2
        while opcode == opcodedesc.EXTENDED_ARG.index:
            opcode = ord(co_code[next_instr])
            next_instr += 3
        if opcode == JUMP_ABSOLUTE:
            return False
    return True

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

pypyjitdriver = PyPyJitDriver(can_inline = can_inline)

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

    def JUMP_ABSOLUTE(f, jumpto, _, ec=None):
        if we_are_jitted():
            f.last_instr = intmask(jumpto)
            ec.bytecode_trace(f)
            jumpto = r_uint(f.last_instr)
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
