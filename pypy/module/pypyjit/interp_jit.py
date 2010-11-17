"""This is not the JIT :-)

This is transformed to become a JIT by code elsewhere: pypy/jit/*
"""

from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import JitDriver, hint, we_are_jitted, dont_look_inside
from pypy.rlib.jit import current_trace_length
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import ObjSpace, Arguments, W_Root
from pypy.interpreter.pycode import PyCode, CO_GENERATOR
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pyopcode import ExitFrame
from opcode import opmap
from pypy.rlib.objectmodel import we_are_translated

PyFrame._virtualizable2_ = ['last_instr', 'pycode',
                            'valuestackdepth', 'valuestack_w[*]',
                            'fastlocals_w[*]',
                            'last_exception',
                            'lastblock',
                            ]

JUMP_ABSOLUTE = opmap['JUMP_ABSOLUTE']

def get_printable_location(next_instr, bytecode):
    from pypy.tool.stdlib_opcode import opcode_method_names
    name = opcode_method_names[ord(bytecode.co_code[next_instr])]
    return '%s #%d %s' % (bytecode.get_repr(), next_instr, name)

def get_jitcell_at(next_instr, bytecode):
    return bytecode.jit_cells.get(next_instr, None)

def set_jitcell_at(newcell, next_instr, bytecode):
    bytecode.jit_cells[next_instr] = newcell

def confirm_enter_jit(next_instr, bytecode, frame, ec):
    return (frame.w_f_trace is None and
            ec.profilefunc is None and
            ec.w_tracefunc is None)

def can_never_inline(next_instr, bytecode):
    return (bytecode.co_flags & CO_GENERATOR) != 0


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

pypyjitdriver = PyPyJitDriver(get_printable_location = get_printable_location,
                              get_jitcell_at = get_jitcell_at,
                              set_jitcell_at = set_jitcell_at,
                              confirm_enter_jit = confirm_enter_jit,
                              can_never_inline = can_never_inline)

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

    def jump_absolute(self, jumpto, _, ec=None):
        if we_are_jitted():
            # Normally, the tick counter is decremented by 100 for every
            # Python opcode.  Here, to better support JIT compilation of
            # small loops, we decrement it by a possibly smaller constant.
            # We get the maximum 100 when the (unoptimized) trace length
            # is at least 3200 (a bit randomly).
            trace_length = r_uint(current_trace_length())
            decr_by = trace_length // 32
            if decr_by < 1:
                decr_by = 1
            elif decr_by > 100:    # also if current_trace_length() returned -1
                decr_by = 100
            #
            self.last_instr = intmask(jumpto)
            ec.bytecode_trace(self, intmask(decr_by))
            jumpto = r_uint(self.last_instr)
        #
        pypyjitdriver.can_enter_jit(frame=self, ec=ec, next_instr=jumpto,
                                    pycode=self.getcode())
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
        msg = "set_param() takes at most 1 non-keyword argument, %d given"
        raise operationerrfmt(space.w_TypeError, msg, len(args_w))
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
            raise operationerrfmt(space.w_TypeError,
                                  "no JIT parameter '%s'", key)

set_param.unwrap_spec = [ObjSpace, Arguments]

@dont_look_inside
def residual_call(space, w_callable, args):
    '''For testing.  Invokes callable(...), but without letting
    the JIT follow the call.'''
    return space.call_args(w_callable, args)
residual_call.unwrap_spec = [ObjSpace, W_Root, Arguments]
