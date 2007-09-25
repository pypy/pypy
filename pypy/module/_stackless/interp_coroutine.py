"""
Coroutine implementation for application level on top
of the internal coroutines.
This is an extensible concept. Multiple implementations
of concurrency can exist together, if they follow the
basic concept of maintaining their own costate.

There is also some diversification possible by using
multiple costates for the same type. This leads to
disjoint switchable sets within the same type.

I'm not so sure to what extent the opposite is possible, too.
I.e., merging the costate of tasklets and greenlets would
allow them to be parents of each other. Needs a bit more
experience to decide where to set the limits.
"""

from pypy.interpreter.baseobjspace import Wrappable, UnpackValueError
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import StaticMethod

from pypy.module._stackless.stackless_flags import StacklessFlags
from pypy.rlib.rcoroutine import Coroutine, BaseCoState, AbstractThunk

from pypy.rlib import rstack # for resume points
from pypy.tool import stdlib_opcode as pythonopcode

class _AppThunk(AbstractThunk):

    def __init__(self, space, costate, w_obj, args):
        self.space = space
        self.costate = costate
        if not space.is_true(space.callable(w_obj)):
            raise OperationError(
                space.w_TypeError, 
                space.mod(space.wrap('object %r is not callable'),
                          space.newtuple([w_obj])))
        self.w_func = w_obj
        self.args = args

    def call(self):
        costate = self.costate
        w_result = self.space.call_args(self.w_func, self.args)
        rstack.resume_point("appthunk", costate, returns=w_result)
        costate.w_tempval = w_result


class AppCoroutine(Coroutine): # XXX, StacklessFlags):

    def __init__(self, space, state=None):
        self.space = space
        if state is None:
            state = AppCoroutine._get_state(space)
        Coroutine.__init__(self, state)
        self.flags = 0
        self.newsubctx()

    def newsubctx(self):
        ec = self.space.getexecutioncontext()
        self.subctx = ec.Subcontext()

    def descr_method__new__(space, w_subtype):
        co = space.allocate_instance(AppCoroutine, w_subtype)
        AppCoroutine.__init__(co, space)
        return space.wrap(co)

    def _get_state(space):
        return space.fromcache(AppCoState)
    _get_state = staticmethod(_get_state)
 
    def w_bind(self, w_func, __args__):
        space = self.space
        if self.frame is not None:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot bind a bound Coroutine"))
        state = self.costate
        thunk = _AppThunk(space, state, w_func, __args__)
        self.bind(thunk)

    def w_switch(self):
        space = self.space
        if self.frame is None:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot switch to an unbound Coroutine"))
        state = self.costate
        self.switch()
        rstack.resume_point("w_switch", state, space)
        w_ret, state.w_tempval = state.w_tempval, space.w_None
        return w_ret

    def w_finished(self, w_excinfo):
        pass

    def finish(self, operror=None):
        space = self.space
        if isinstance(operror, OperationError):
            w_exctype = operror.w_type
            w_excvalue = operror.w_value
            w_exctraceback = operror.application_traceback
            w_excinfo = space.newtuple([w_exctype, w_excvalue, w_exctraceback])
        else:
            w_N = space.w_None
            w_excinfo = space.newtuple([w_N, w_N, w_N])

        return space.call_method(space.wrap(self),'finished', w_excinfo)

    def hello(self):
        ec = self.space.getexecutioncontext()
        self.subctx.enter(ec)

    def goodbye(self):
        ec = self.space.getexecutioncontext()
        self.subctx.leave(ec)

    def w_kill(self):
        self.kill()

    def _userdel(self):
        if self.get_is_zombie():
            return
        self.set_is_zombie(True)
        self.space.userdel(self.space.wrap(self))

    def w_getcurrent(space):
        return space.wrap(AppCoroutine._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)

    def w_getmain(space):
        return space.wrap(AppCoroutine._get_state(space).main)
    w_getmain = staticmethod(w_getmain)

    # pickling interface
    def descr__reduce__(self, space):
        # this is trying to be simplistic at the moment.
        # we neither allow to pickle main (which can become a mess
        # since it has some deep anchestor frames)
        # nor we allow to pickle the current coroutine.
        # rule: switch before pickling.
        # you cannot construct the tree that you are climbing.
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('_stackless')
        mod      = space.interp_w(MixedModule, w_mod)
        w_mod2    = space.getbuiltinmodule('_pickle_support')
        mod2      = space.interp_w(MixedModule, w_mod2)
        w_new_inst = mod.get('coroutine')
        w        = space.wrap
        nt = space.newtuple
        ec = self.space.getexecutioncontext()

        if self is self.costate.main:
            return nt([mod.get('_return_main'), nt([])])

        thunk = self.thunk
        if isinstance(thunk, _AppThunk):
            w_args, w_kwds = thunk.args.topacked()
            w_thunk = nt([thunk.w_func, w_args, w_kwds])
        else:
            w_thunk = space.w_None

        tup_base = [
            ]
        tup_state = [
            w(self.flags),
            self.subctx.getstate(space),
            w_thunk,
            w(self.parent),
            ]

        return nt([w_new_inst, nt(tup_base), nt(tup_state)])

    def descr__setstate__(self, space, w_args):
        try:
            w_flags, w_state, w_thunk, w_parent = space.unpackiterable(w_args,
                                                             expected_length=4)
        except UnpackValueError, e:
            raise OperationError(space.w_ValueError, space.wrap(e.msg))
        self.flags = space.int_w(w_flags)
        if space.is_w(w_parent, space.w_None):
            w_parent = self.w_getmain(space)
        self.parent = space.interp_w(AppCoroutine, w_parent)
        ec = self.space.getexecutioncontext()
        self.subctx.setstate(self.space, w_state)
        self.reconstruct_framechain()
        if space.is_w(w_thunk, space.w_None):
            self.thunk = None
        else:
            try:
                w_func, w_args, w_kwds = space.unpackiterable(w_thunk,
                                                             expected_length=3)
            except UnpackValueError, e:
                raise OperationError(space.w_ValueError, space.wrap(e.msg))
            args = Arguments.frompacked(space, w_args, w_kwds)
            self.bind(_AppThunk(space, self.costate, w_func, args))

    def reconstruct_framechain(self):
        from pypy.interpreter.pyframe import PyFrame
        from pypy.rlib.rstack import resume_state_create
        if self.subctx.framestack.empty():
            self.frame = None
            return

        space = self.space
        ec = space.getexecutioncontext()
        costate = self.costate
        # now the big fun of recreating tiny things...
        bottom = resume_state_create(None, "yield_current_frame_to_caller_1")
        # ("coroutine__bind", state)
        _bind_frame = resume_state_create(bottom, "coroutine__bind", costate)
        # ("appthunk", costate, returns=w_result)
        appthunk_frame = resume_state_create(_bind_frame, "appthunk", costate)
        chain = appthunk_frame
        for frame in self.subctx.framestack.items:
            assert isinstance(frame, PyFrame)
            # ("execute_frame", self, executioncontext, returns=w_exitvalue)
            chain = resume_state_create(chain, "execute_frame", frame, ec)
            code = frame.pycode.co_code
            # ("dispatch", self, co_code, ec, returns=next_instr)
            chain = resume_state_create(chain, "dispatch", frame, code, ec)
            # ("handle_bytecode", self, co_code, ec, returns=next_instr)
            chain = resume_state_create(chain, "handle_bytecode", frame, code,
                                        ec)
            instr = frame.last_instr
            opcode = ord(code[instr])
            map = pythonopcode.opmap
            call_ops = [map['CALL_FUNCTION'], map['CALL_FUNCTION_KW'], map['CALL_FUNCTION_VAR'], 
                        map['CALL_FUNCTION_VAR_KW'], map['CALL_METHOD']]
            assert opcode in call_ops
            # ("dispatch_call", self, co_code, next_instr, ec)
            chain = resume_state_create(chain, "dispatch_call", frame, code,
                                        instr+3, ec)
            instr += 1
            oparg = ord(code[instr]) | ord(code[instr + 1]) << 8
            nargs = oparg & 0xff
            if space.config.objspace.opcodes.CALL_METHOD and opcode == map['CALL_METHOD']:
                chain = resume_state_create(chain, 'CALL_METHOD', frame,
                                            nargs)
            elif opcode == map['CALL_FUNCTION'] and (oparg >> 8) & 0xff == 0:
                # Only positional arguments
                # case1: ("CALL_FUNCTION", f, nargs, returns=w_result)
                chain = resume_state_create(chain, 'CALL_FUNCTION', frame,
                                            nargs)
            else:
                # case2: ("call_function", f, returns=w_result)
                chain = resume_state_create(chain, 'call_function', frame)

        # ("w_switch", state, space)
        w_switch_frame = resume_state_create(chain, 'w_switch', costate, space)
        # ("coroutine_switch", state, returns=incoming_frame)
        switch_frame = resume_state_create(w_switch_frame, "coroutine_switch", costate)
        self.frame = switch_frame

# _mixin_ did not work
for methname in StacklessFlags.__dict__:
    meth = getattr(StacklessFlags, methname)
    if hasattr(meth, 'im_func'):
        setattr(AppCoroutine, meth.__name__, meth.im_func)
del meth, methname

def w_get_is_zombie(space, self):
    return space.wrap(self.get_is_zombie())
AppCoroutine.w_get_is_zombie = w_get_is_zombie

def w_get_is_alive(space, self):
    return space.wrap(self.is_alive())
AppCoroutine.w_get_is_alive = w_get_is_alive

def w_descr__framestack(space, self):
    assert isinstance(self, AppCoroutine)
    if self.subctx.framestack is not None:
        items = [space.wrap(item) for item in self.subctx.framestack.items]
        return space.newtuple(items)
    else:
        return space.newtuple([])

def makeStaticMethod(module, classname, funcname):
    space = module.space
    w_klass = space.getattr(space.wrap(module), space.wrap(classname))
    # HACK HACK HACK
    # make the typeobject mutable for a while
    from pypy.objspace.std.typeobject import _HEAPTYPE, W_TypeObject
    assert isinstance(w_klass, W_TypeObject)
    old_flags = w_klass.__flags__
    w_klass.__flags__ |= _HEAPTYPE
    
    space.appexec([w_klass, space.wrap(funcname)], """
        (klass, funcname):
            func = getattr(klass, funcname)
            setattr(klass, funcname, staticmethod(func.im_func))
    """)
    w_klass.__flags__ = old_flags

def post_install(module):
    makeStaticMethod(module, 'coroutine', 'getcurrent')
    makeStaticMethod(module, 'coroutine', 'getmain')
    space = module.space
    AppCoroutine._get_state(space).post_install()

# space.appexec("""() :

# maybe use __spacebind__ for postprocessing

AppCoroutine.typedef = TypeDef("coroutine",
    __new__ = interp2app(AppCoroutine.descr_method__new__.im_func),
    bind = interp2app(AppCoroutine.w_bind,
                      unwrap_spec=['self', W_Root, Arguments]),
    switch = interp2app(AppCoroutine.w_switch),
    kill = interp2app(AppCoroutine.w_kill),
    finished = interp2app(AppCoroutine.w_finished),
    is_alive = GetSetProperty(AppCoroutine.w_get_is_alive),
    is_zombie = GetSetProperty(AppCoroutine.w_get_is_zombie,
      doc=AppCoroutine.get_is_zombie.__doc__), #--- this flag is a bit obscure
      # and not useful (it's totally different from Coroutine.is_zombie(), too)
      # but lib/stackless.py uses it
    _framestack = GetSetProperty(w_descr__framestack),
    getcurrent = interp2app(AppCoroutine.w_getcurrent),
    getmain = interp2app(AppCoroutine.w_getmain),
    __reduce__   = interp2app(AppCoroutine.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(AppCoroutine.descr__setstate__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
    __module__ = '_stackless',
)

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.w_tempval = space.w_None
        self.space = space
        
    def post_install(self):
        self.current = self.main = AppCoroutine(self.space, state=self)
        self.main.subctx.framestack = None    # wack

def return_main(space):
    return AppCoroutine._get_state(space).main
return_main.unwrap_spec = [ObjSpace]
