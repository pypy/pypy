"""This is not the JIT :-)

This is transformed to become a JIT by code elsewhere: pypy/jit/*
"""

from pypy.tool.pairtype import extendabletype
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.jit import JitDriver, hint, we_are_jitted, dont_look_inside
from pypy.rlib.jit import current_trace_length, unroll_parameters
import pypy.interpreter.pyopcode   # for side-effects
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.pycode import PyCode, CO_GENERATOR
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pyopcode import ExitFrame
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from opcode import opmap
from pypy.rlib.nonconst import NonConstant
from pypy.jit.metainterp.resoperation import rop
from pypy.module.pypyjit.interp_resop import debug_merge_point_from_boxes

PyFrame._virtualizable2_ = ['last_instr', 'pycode',
                            'valuestackdepth', 'locals_stack_w[*]',
                            'cells[*]',
                            'last_exception',
                            'lastblock',
                            'is_being_profiled',
                            ]

JUMP_ABSOLUTE = opmap['JUMP_ABSOLUTE']

def get_printable_location(next_instr, is_being_profiled, bytecode):
    from pypy.tool.stdlib_opcode import opcode_method_names
    name = opcode_method_names[ord(bytecode.co_code[next_instr])]
    return '%s #%d %s' % (bytecode.get_repr(), next_instr, name)

def get_jitcell_at(next_instr, is_being_profiled, bytecode):
    return bytecode.jit_cells.get((next_instr, is_being_profiled), None)

def set_jitcell_at(newcell, next_instr, is_being_profiled, bytecode):
    bytecode.jit_cells[next_instr, is_being_profiled] = newcell

def confirm_enter_jit(next_instr, is_being_profiled, bytecode, frame, ec):
    return (frame.w_f_trace is None and
            ec.w_tracefunc is None)

def can_never_inline(next_instr, is_being_profiled, bytecode):
    return (bytecode.co_flags & CO_GENERATOR) != 0


def wrap_oplist(space, logops, operations):
    list_w = []
    for op in operations:
        if op.getopnum() == rop.DEBUG_MERGE_POINT:
            list_w.append(space.wrap(debug_merge_point_from_boxes(
                op.getarglist())))
        else:
            list_w.append(space.wrap(logops.repr_of_resop(op)))
    return list_w

class PyPyJitDriver(JitDriver):
    reds = ['frame', 'ec']
    greens = ['next_instr', 'is_being_profiled', 'pycode']
    virtualizables = ['frame']

    def on_compile(self, logger, looptoken, operations, type, next_instr,
                   is_being_profiled, ll_pycode):
        from pypy.rpython.annlowlevel import cast_base_ptr_to_instance

        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_compile_hook):
            logops = logger._make_log_operations()
            list_w = wrap_oplist(space, logops, operations)
            pycode = cast_base_ptr_to_instance(PyCode, ll_pycode)
            cache.in_recursion = True
            try:
                space.call_function(cache.w_compile_hook,
                                    space.wrap('main'),
                                    space.wrap(type),
                                    space.newtuple([pycode,
                                    space.wrap(next_instr),
                                    space.wrap(is_being_profiled)]),
                                    space.newlist(list_w))
            except OperationError, e:
                e.write_unraisable(space, "jit hook ", cache.w_compile_hook)
            cache.in_recursion = False

    def on_compile_bridge(self, logger, orig_looptoken, operations, n):
        space = self.space
        cache = space.fromcache(Cache)
        if cache.in_recursion:
            return
        if space.is_true(cache.w_compile_hook):
            logops = logger._make_log_operations()
            list_w = wrap_oplist(space, logops, operations)
            cache.in_recursion = True
            try:
                space.call_function(cache.w_compile_hook,
                                    space.wrap('main'),
                                    space.wrap('bridge'),
                                    space.wrap(n),
                                    space.newlist(list_w))
            except OperationError, e:
                e.write_unraisable(space, "jit hook ", cache.w_compile_hook)
            cache.in_recursion = False

pypyjitdriver = PyPyJitDriver(get_printable_location = get_printable_location,
                              get_jitcell_at = get_jitcell_at,
                              set_jitcell_at = set_jitcell_at,
                              confirm_enter_jit = confirm_enter_jit,
                              can_never_inline = can_never_inline)

class __extend__(PyFrame):

    def dispatch(self, pycode, next_instr, ec):
        self = hint(self, access_directly=True)
        next_instr = r_uint(next_instr)
        is_being_profiled = self.is_being_profiled
        try:
            while True:
                pypyjitdriver.jit_merge_point(ec=ec,
                    frame=self, next_instr=next_instr, pycode=pycode,
                    is_being_profiled=is_being_profiled)
                co_code = pycode.co_code
                self.valuestackdepth = hint(self.valuestackdepth, promote=True)
                next_instr = self.handle_bytecode(co_code, next_instr, ec)
                is_being_profiled = self.is_being_profiled
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
                                    pycode=self.getcode(),
                                    is_being_profiled=self.is_being_profiled)
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

def set_param(space, __args__):
    '''Configure the tunable JIT parameters.
        * set_param(name=value, ...)            # as keyword arguments
        * set_param("name=value,name=value")    # as a user-supplied string
        * set_param("off")                      # disable the jit
        * set_param("default")                  # restore all defaults
    '''
    # XXXXXXXXX
    args_w, kwds_w = __args__.unpack()
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
        if key == 'enable_opts':
            pypyjitdriver.set_param('enable_opts', space.str_w(w_value))
        else:
            intval = space.int_w(w_value)
            for name, _ in unroll_parameters:
                if name == key and name != 'enable_opts':
                    pypyjitdriver.set_param(name, intval)
                    break
            else:
                raise operationerrfmt(space.w_TypeError,
                                      "no JIT parameter '%s'", key)

@dont_look_inside
def residual_call(space, w_callable, __args__):
    '''For testing.  Invokes callable(...), but without letting
    the JIT follow the call.'''
    return space.call_args(w_callable, __args__)

class Cache(object):
    in_recursion = False

    def __init__(self, space):
        self.w_compile_hook = space.w_None

@unwrap_spec(ObjSpace, W_Root)
def set_compile_hook(space, w_hook):
    """ set_compile_hook(hook)

    Set a compiling hook that will be called each time a loop is compiled.
    The hook will be called with the following signature:
    hook(merge_point_type, loop_type, greenkey or guard_number, operations)

    for now merge point type is always `main`

    loop_type can be either `loop` `entry_bridge` or `bridge`
    in case loop is not `bridge`, greenkey will be a set of constants
    for jit merge point. in case it's `main` it'll be a tuple
    (code, offset, is_being_profiled)

    Note that jit hook is not reentrant. It means that if the code
    inside the jit hook is itself jitted, it will get compiled, but the
    jit hook won't be called for that.

    XXX write down what else
    """
    cache = space.fromcache(Cache)
    cache.w_compile_hook = w_hook
    cache.in_recursion = NonConstant(False)
    return space.w_None
