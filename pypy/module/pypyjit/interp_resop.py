
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import unwrap_spec, interp2app, NoneNotWrapped
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.jit.metainterp.resoperation import rop, AbstractResOp
from pypy.rlib.nonconst import NonConstant
from pypy.rlib import jit_hooks

class Cache(object):
    in_recursion = False

    def __init__(self, space):
        self.w_compile_hook = space.w_None
        self.w_abort_hook = space.w_None

def wrap_greenkey(space, jitdriver, greenkey):
    if jitdriver.name == 'pypyjit':
        next_instr = greenkey[0].getint()
        is_being_profiled = greenkey[1].getint()
        ll_code = lltype.cast_opaque_ptr(lltype.Ptr(OBJECT),
                                         greenkey[2].getref_base())
        pycode = cast_base_ptr_to_instance(PyCode, ll_code)
        return space.newtuple([space.wrap(pycode), space.wrap(next_instr),
                               space.newbool(bool(is_being_profiled))])
    else:
        return space.wrap('who knows?')

def set_compile_hook(space, w_hook):
    """ set_compile_hook(hook)

    Set a compiling hook that will be called each time a loop is compiled.
    The hook will be called with the following signature:
    hook(jitdriver_name, loop_type, greenkey or guard_number, operations,
         assembler_addr, assembler_length)

    jitdriver_name is the name of this particular jitdriver, 'pypyjit' is
    the main interpreter loop

    loop_type can be either `loop` `entry_bridge` or `bridge`
    in case loop is not `bridge`, greenkey will be a tuple of constants
    or a string describing it.

    for the interpreter loop` it'll be a tuple
    (code, offset, is_being_profiled)

    assembler_addr is an integer describing where assembler starts,
    can be accessed via ctypes, assembler_lenght is the lenght of compiled
    asm

    Note that jit hook is not reentrant. It means that if the code
    inside the jit hook is itself jitted, it will get compiled, but the
    jit hook won't be called for that.
    """
    cache = space.fromcache(Cache)
    cache.w_compile_hook = w_hook
    cache.in_recursion = NonConstant(False)
    return space.w_None

def set_abort_hook(space, w_hook):
    """ set_abort_hook(hook)

    Set a hook (callable) that will be called each time there is tracing
    aborted due to some reason.

    The hook will be called as in: hook(jitdriver_name, greenkey, reason)

    Where reason is the reason for abort, see documentation for set_compile_hook
    for descriptions of other arguments.
    """
    cache = space.fromcache(Cache)
    cache.w_abort_hook = w_hook
    cache.in_recursion = NonConstant(False)
    return space.w_None

def wrap_oplist(space, logops, operations, ops_offset):
    return [WrappedOp(jit_hooks._cast_to_gcref(op),
                      ops_offset[op],
                      logops.repr_of_resop(op)) for op in operations]

@unwrap_spec(num=int, offset=int, repr=str)
def descr_new_resop(space, num, w_args, w_res=NoneNotWrapped, offset=-1,
                    repr=''):
    args = [jit_hooks.boxint_new(space.int_w(w_arg)) for w_arg in w_args]
    if w_res is None:
        llres = lltype.nullptr(llmemory.GCREF)
    else:
        llres = jit_hooks.boxint_new(space.int_w(w_res))
    return WrappedOp(jit_hooks.resop_new(num, args, llres), offset, repr)

class WrappedOp(Wrappable):
    """ A class representing a single ResOperation, wrapped nicely
    """
    def __init__(self, op, offset, repr_of_resop):
        self.op = op
        self.offset = offset
        self.repr_of_resop = repr_of_resop

    def descr_repr(self, space):
        return space.wrap(self.repr_of_resop)

    def descr_num(self, space):
        return space.wrap(jit_hooks.resop_opnum(self.op))

WrappedOp.typedef = TypeDef(
    'ResOperation',
    __doc__ = WrappedOp.__doc__,
    __new__ = interp2app(descr_new_resop),
    __repr__ = interp2app(WrappedOp.descr_repr),
    num = GetSetProperty(WrappedOp.descr_num),
)
WrappedOp.acceptable_as_base_class = False
