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

PyFrame._virtualizable2_ = ['last_instr', 'pycode',
                            'valuestackdepth', 'valuestack_w[*]',
                            'fastlocals_w[*]', 'f_forward',
                            ]

JUMP_ABSOLUTE = opmap['JUMP_ABSOLUTE']

def can_inline(next_instr, bytecode):
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

def get_printable_location(next_instr, bytecode):
    from pypy.tool.stdlib_opcode import opcode_method_names
    name = opcode_method_names[ord(bytecode.co_code[next_instr])]
    return '%s #%d %s' % (bytecode.get_repr(), next_instr, name)

def leave(next_instr, pycode, frame, ec):
    from pypy.interpreter.executioncontext import ExecutionContext
    # can't use a method here, since this function is seen later than the main
    # annotation       XXX no longer true, could be fixed
    ExecutionContext._jit_rechain_frame(ec, frame)

def get_jitcell_at(next_instr, bytecode):
    return bytecode.jit_cells.get(next_instr, None)

def set_jitcell_at(newcell, next_instr, bytecode):
    bytecode.jit_cells[next_instr] = newcell


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

pypyjitdriver = PyPyJitDriver(can_inline = can_inline,
                              get_printable_location = get_printable_location,
                              leave = leave,
                              get_jitcell_at = get_jitcell_at,
                              set_jitcell_at = set_jitcell_at)

class __extend__(PyFrame):

    def dispatch(self, pycode, next_instr, ec):
        self = hint(self, access_directly=True)
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


PyCode__initialize = PyCode._initialize

class __extend__(PyCode):
    __metaclass__ = extendabletype

    def _initialize(self):
        PyCode__initialize(self)
        self.jit_cells = {}

    def _freeze_(self):
        self.jit_cells = {}
        return False

# ____________________________________________________________
#
# Public interface    

def set_param(space, args):
    '''Configure the tunable JIT parameters.
        * set_param(name=value, ...)            # as keyword arguments
        * set_param("name=value,name=value")    # as a user-supplied string
    '''
    # XXXXXXXXX
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
