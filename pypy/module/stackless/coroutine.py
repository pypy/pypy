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

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import StaticMethod

from pypy.module.stackless.stackless_flags import StacklessFlags
from pypy.module.stackless.interp_coroutine import Coroutine, BaseCoState, AbstractThunk

from pypy.rpython import rstack # for resume points
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

    def __init__(self, space, is_main=False):
        self.space = space
        state = self._get_state(space)
        Coroutine.__init__(self, state)
        self.flags = 0
        self.framestack = None
        if not is_main:
             space.getexecutioncontext().subcontext_new(self)

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
        self.switch()
        rstack.resume_point("w_switch", self, space)
        state = self.costate
        w_ret, state.w_tempval = state.w_tempval, space.w_None
        return w_ret

    def hello(self):
        ec = self.space.getexecutioncontext()
        ec.subcontext_enter(self)

    def goodbye(self):
        ec = self.space.getexecutioncontext()
        ec.subcontext_leave(self)

    def w_kill(self):
        self.kill()

    def _userdel(self):
        if self.get_is_zombie():
            return
        self.set_is_zombie(True)
        self.space.userdel(self)

    def w_getcurrent(space):
        return space.wrap(AppCoroutine._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)

    # pickling interface
    def descr__reduce__(self, space):
        # this is trying to be simplistic at the moment.
        # we neither allow to pickle main (which can become a mess
        # since it has some deep anchestor frames)
        # nor we allowto pickle the current coroutine.
        # rule: switch before pickling.
        # you cannot construct the tree that you are climbing.
        # XXX missing checks!
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod    = space.getbuiltinmodule('stackless')
        mod      = space.interp_w(MixedModule, w_mod)
        w_mod2    = space.getbuiltinmodule('_pickle_support')
        mod2      = space.interp_w(MixedModule, w_mod2)
        new_inst = mod.get('coroutine')
        w        = space.wrap
        nt = space.newtuple
        ec = self.space.getexecutioncontext()

        if self is self._get_state(space).main:
            return space.newtuple([mod2.get('return_main'), space.newtuple([])])

        tup_base = [
            ]
        tup_state = [
            w(self.flags),
            ec.subcontext_getstate(self),
            ]

        return nt([new_inst, nt(tup_base), nt(tup_state)])

    def descr__setstate__(self, space, w_args):
        args_w = space.unpackiterable(w_args)
        w_flags, w_state = args_w
        self.flags = space.int_w(w_flags)
        ec = self.space.getexecutioncontext()
        ec.subcontext_setstate(self, w_state)
        self.reconstruct_framechain()
        
    def reconstruct_framechain(self):
        from pypy.interpreter.pyframe import PyFrame
        from pypy.rpython.rstack import resume_state_create
        if self.framestack.empty():
            self.frame = None
            return

        space = self.space
        ec = space.getexecutioncontext()
        costate = self.costate
        # now the big fun of recreating tiny things...
        bottom = resume_state_create(None, "yield_current_frame_to_caller_1")
        # resume_point("coroutine__bind", self, state)
        _bind_frame = resume_state_create(bottom, "coroutine__bind", self, costate)
        # rstack.resume_point("appthunk", costate, returns=w_result)
        appthunk_frame = resume_state_create(_bind_frame, "appthunk", costate)
        chain = appthunk_frame
        for frame in self.framestack.items:
            assert isinstance(frame, PyFrame)
            # rstack.resume_point("evalframe", self, executioncontext, returns=result)
            evalframe_frame = resume_state_create(chain, "evalframe", frame, ec)
            # rstack.resume_point("eval", self, executioncontext)
            eval_frame = resume_state_create(evalframe_frame, "eval", frame, ec)
            # rstack.resume_point("dispatch_call", self, code, ec)
            code = frame.getcode().co_code
            dispatch_call_frame = resume_state_create(eval_frame, "dispatch_call", frame, code, ec)
            instr = frame.last_instr
            opcode = ord(code[instr])
            assert opcode == pythonopcode.opmap['CALL_FUNCTION']
            instr += 1
            oparg = ord(code[instr]) | ord(code[instr + 1]) << 8
            if (oparg >> 8) & 0xff == 0:
                # Only positional arguments
                nargs = oparg & 0xff
                # case1: rstack.resume_point("CALL_FUNCTION", f, nargs, returns=w_result)
                call_frame = resume_state_create(dispatch_call_frame, 'CALL_FUNCTION', frame, nargs)
            else:
                # case2: rstack.resume_point("call_function", f, returns=w_result)
                call_frame = resume_state_create(dispatch_call_frame, 'call_function', frame)
            chain = call_frame

        # rstack.resume_point("w_switch", self, space)
        w_switch_frame = resume_state_create(chain, 'w_switch', self, space)
        # resume_point("coroutine_switch", self, state, returns=incoming_frame)
        switch_frame = resume_state_create(w_switch_frame, "coroutine_switch", self, costate)
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

def w_descr__framestack(space, self):
    assert isinstance(self, AppCoroutine)
    if self.framestack:
        items = [space.wrap(item) for item in self.framestack.items]
        return space.newtuple(items)
    else:
        return space.newtuple([])

def makeStaticMethod(module, classname, funcname):
    space = module.space
    space.appexec(map(space.wrap, (module, classname, funcname)), """
        (module, klassname, funcname):
            klass = getattr(module, klassname)
            func = getattr(klass, funcname)
            setattr(klass, funcname, staticmethod(func.im_func))
    """)

def post_install(module):
    makeStaticMethod(module, 'coroutine', 'getcurrent')
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
    is_zombie = GetSetProperty(AppCoroutine.w_get_is_zombie, doc=AppCoroutine.get_is_zombie.__doc__),
    _framestack = GetSetProperty(w_descr__framestack),
    getcurrent = interp2app(AppCoroutine.w_getcurrent),
    __reduce__   = interp2app(AppCoroutine.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(AppCoroutine.descr__setstate__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
    __module__ = 'stackless',
)

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.w_tempval = space.w_None
        self.space = space
        
    def post_install(self):
        self.current = self.main = self.last = AppCoroutine(self.space, is_main=True)
