
from pypy.interpreter.typedef import (TypeDef, GetSetProperty,
     interp_attrproperty, interp_attrproperty_w)
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import unwrap_spec, interp2app, NoneNotWrapped
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance, hlstr
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.jit.metainterp.resoperation import rop, AbstractResOp
from pypy.rlib.nonconst import NonConstant
from pypy.rlib import jit_hooks
from pypy.module.pypyjit.interp_jit import pypyjitdriver

class Cache(object):
    in_recursion = False

    def __init__(self, space):
        self.w_compile_hook = space.w_None
        self.w_abort_hook = space.w_None
        self.w_optimize_hook = space.w_None

def wrap_greenkey(space, jitdriver, greenkey, greenkey_repr):
    if greenkey is None:
        return space.w_None
    jitdriver_name = jitdriver.name
    if jitdriver_name == 'pypyjit':
        next_instr = greenkey[0].getint()
        is_being_profiled = greenkey[1].getint()
        ll_code = lltype.cast_opaque_ptr(lltype.Ptr(OBJECT),
                                         greenkey[2].getref_base())
        pycode = cast_base_ptr_to_instance(PyCode, ll_code)
        return space.newtuple([space.wrap(pycode), space.wrap(next_instr),
                               space.newbool(bool(is_being_profiled))])
    else:
        return space.wrap(greenkey_repr)

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

def set_optimize_hook(space, w_hook):
    """ set_optimize_hook(hook)

    Set a compiling hook that will be called each time a loop is optimized,
    but before assembler compilation. This allows to add additional
    optimizations on Python level.

    The hook will be called with the following signature:
    hook(jitdriver_name, loop_type, greenkey or guard_number, operations)

    jitdriver_name is the name of this particular jitdriver, 'pypyjit' is
    the main interpreter loop

    loop_type can be either `loop` `entry_bridge` or `bridge`
    in case loop is not `bridge`, greenkey will be a tuple of constants
    or a string describing it.

    for the interpreter loop` it'll be a tuple
    (code, offset, is_being_profiled)

    Note that jit hook is not reentrant. It means that if the code
    inside the jit hook is itself jitted, it will get compiled, but the
    jit hook won't be called for that.

    Result value will be the resulting list of operations, or None
    """
    cache = space.fromcache(Cache)
    cache.w_optimize_hook = w_hook
    cache.in_recursion = NonConstant(False)

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

def wrap_oplist(space, logops, operations, ops_offset=None):
    l_w = []
    jitdrivers_sd = logops.metainterp_sd.jitdrivers_sd
    for op in operations:
        if ops_offset is None:
            ofs = -1
        else:
            ofs = ops_offset.get(op, 0)
        if op.opnum == rop.DEBUG_MERGE_POINT:
            jd_sd = jitdrivers_sd[op.getarg(0).getint()]
            greenkey = op.getarglist()[3:]
            repr = jd_sd.warmstate.get_location_str(greenkey)
            w_greenkey = wrap_greenkey(space, jd_sd.jitdriver, greenkey, repr)
            l_w.append(DebugMergePoint(space, jit_hooks._cast_to_gcref(op),
                                       logops.repr_of_resop(op),
                                       jd_sd.jitdriver.name,
                                       op.getarg(1).getint(),
                                       op.getarg(2).getint(),
                                       w_greenkey))
        else:
            l_w.append(WrappedOp(jit_hooks._cast_to_gcref(op), ofs,
                                 logops.repr_of_resop(op)))
    return l_w

class WrappedBox(Wrappable):
    """ A class representing a single box
    """
    def __init__(self, llbox):
        self.llbox = llbox

    def descr_getint(self, space):
        return space.wrap(jit_hooks.box_getint(self.llbox))

@unwrap_spec(no=int)
def descr_new_box(space, w_tp, no):
    return WrappedBox(jit_hooks.boxint_new(no))

WrappedBox.typedef = TypeDef(
    'Box',
    __new__ = interp2app(descr_new_box),
    getint = interp2app(WrappedBox.descr_getint),
)

@unwrap_spec(num=int, offset=int, repr=str, res=WrappedBox)
def descr_new_resop(space, w_tp, num, w_args, res, offset=-1,
                    repr=''):
    args = [space.interp_w(WrappedBox, w_arg).llbox for w_arg in
            space.listview(w_args)]
    if res is None:
        llres = jit_hooks.emptyval()
    else:
        llres = res.llbox
    return WrappedOp(jit_hooks.resop_new(num, args, llres), offset, repr)

@unwrap_spec(repr=str, jd_name=str, call_depth=int, call_id=int)
def descr_new_dmp(space, w_tp, w_args, repr, jd_name, call_depth, call_id,
    w_greenkey):

    args = [space.interp_w(WrappedBox, w_arg).llbox for w_arg in
            space.listview(w_args)]
    num = rop.DEBUG_MERGE_POINT
    return DebugMergePoint(space,
                           jit_hooks.resop_new(num, args, jit_hooks.emptyval()),
                           repr, jd_name, call_depth, call_id, w_greenkey)

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
        return space.wrap(jit_hooks.resop_getopnum(self.op))

    def descr_name(self, space):
        return space.wrap(hlstr(jit_hooks.resop_getopname(self.op)))

    @unwrap_spec(no=int)
    def descr_getarg(self, space, no):
        return WrappedBox(jit_hooks.resop_getarg(self.op, no))

    @unwrap_spec(no=int, box=WrappedBox)
    def descr_setarg(self, space, no, box):
        jit_hooks.resop_setarg(self.op, no, box.llbox)

    def descr_getresult(self, space):
        return WrappedBox(jit_hooks.resop_getresult(self.op))

    def descr_setresult(self, space, w_box):
        box = space.interp_w(WrappedBox, w_box)
        jit_hooks.resop_setresult(self.op, box.llbox)

class DebugMergePoint(WrappedOp):
    def __init__(self, space, op, repr_of_resop, jd_name, call_depth, call_id,
        w_greenkey):

        WrappedOp.__init__(self, op, -1, repr_of_resop)
        self.jd_name = jd_name
        self.call_depth = call_depth
        self.call_id = call_id
        self.w_greenkey = w_greenkey

    def get_pycode(self, space):
        if self.jd_name == pypyjitdriver.name:
            return space.getitem(self.w_greenkey, space.wrap(0))
        raise OperationError(space.w_AttributeError, space.wrap("This DebugMergePoint doesn't belong to the main Python JitDriver"))

    def get_bytecode_no(self, space):
        if self.jd_name == pypyjitdriver.name:
            return space.getitem(self.w_greenkey, space.wrap(1))
        raise OperationError(space.w_AttributeError, space.wrap("This DebugMergePoint doesn't belong to the main Python JitDriver"))

    def get_jitdriver_name(self, space):
        return space.wrap(self.jd_name)

WrappedOp.typedef = TypeDef(
    'ResOperation',
    __doc__ = WrappedOp.__doc__,
    __new__ = interp2app(descr_new_resop),
    __repr__ = interp2app(WrappedOp.descr_repr),
    num = GetSetProperty(WrappedOp.descr_num),
    name = GetSetProperty(WrappedOp.descr_name),
    getarg = interp2app(WrappedOp.descr_getarg),
    setarg = interp2app(WrappedOp.descr_setarg),
    result = GetSetProperty(WrappedOp.descr_getresult,
                            WrappedOp.descr_setresult)
)
WrappedOp.acceptable_as_base_class = False

DebugMergePoint.typedef = TypeDef(
    'DebugMergePoint', WrappedOp.typedef,
    __new__ = interp2app(descr_new_dmp),
    greenkey = interp_attrproperty_w("w_greenkey", cls=DebugMergePoint),
    pycode = GetSetProperty(DebugMergePoint.get_pycode),
    bytecode_no = GetSetProperty(DebugMergePoint.get_bytecode_no),
    call_depth = interp_attrproperty("call_depth", cls=DebugMergePoint),
    call_id = interp_attrproperty("call_id", cls=DebugMergePoint),
    jitdriver_name = GetSetProperty(DebugMergePoint.get_jitdriver_name),
)
DebugMergePoint.acceptable_as_base_class = False


