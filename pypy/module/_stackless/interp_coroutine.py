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
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.function import StaticMethod

from pypy.module._stackless.stackless_flags import StacklessFlags
from pypy.module._stackless.rcoroutine import Coroutine, BaseCoState, AbstractThunk, CoroutineExit

from pypy.module.exceptions.interp_exceptions import W_SystemExit, _new_exception

from pypy.rlib import rstack, jit # for resume points
from pypy.tool import stdlib_opcode as pythonopcode

class _AppThunk(AbstractThunk):

    def __init__(self, space, costate, w_obj, args):
        self.space = space
        self.costate = costate
        if not space.is_true(space.callable(w_obj)):
            raise operationerrfmt(
                space.w_TypeError, 
                "'%s' object is not callable",
                space.type(w_obj).getname(space, '?'))
        self.w_func = w_obj
        self.args = args

    def call(self):
        costate = self.costate
        w_result = self.space.call_args(self.w_func, self.args)
        rstack.resume_point("appthunk", costate, returns=w_result)
        costate.w_tempval = w_result

class _ResumeThunk(AbstractThunk):
    def __init__(self, space, costate, w_frame):
        self.space = space
        self.costate = costate
        self.w_frame = w_frame

    def call(self):
        w_result = resume_frame(self.space, self.w_frame)
        # costate.w_tempval = w_result #XXX?


W_CoroutineExit = _new_exception('CoroutineExit', W_SystemExit,
                        """Coroutine killed manually.""")

# Should be moved to interp_stackless.py if it's ever implemented... Currently
# used by pypy/lib/stackless.py.
W_TaskletExit = _new_exception('TaskletExit', W_SystemExit, 
            """Tasklet killed manually.""")

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

    def switch(self):
        space = self.space
        try:
            Coroutine.switch(self)
        except CoroutineExit:
            raise OperationError(self.costate.w_CoroutineExit, space.w_None)

    def w_finished(self, w_excinfo):
        pass

    def finish(self, operror=None):
        space = self.space
        if isinstance(operror, OperationError):
            w_exctype = operror.w_type
            w_excvalue = operror.get_w_value(space)
            w_exctraceback = operror.application_traceback
            w_excinfo = space.newtuple([w_exctype, w_excvalue, w_exctraceback])
            
            if w_exctype is self.costate.w_CoroutineExit:
                self.coroutine_exit = True
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
            
    def w_throw(self, w_type, w_value=None, w_traceback=None):
        space = self.space

        operror = OperationError(w_type, w_value)
        operror.normalize_exception(space)
        
        if not space.is_w(w_traceback, space.w_None):
            from pypy.interpreter import pytraceback
            tb = space.interpclass_w(w_traceback)
            if tb is None or not space.is_true(space.isinstance(tb, 
                space.gettypeobject(pytraceback.PyTraceback.typedef))):
                raise OperationError(space.w_TypeError,
                      space.wrap("throw: arg 3 must be a traceback or None"))
            operror.application_traceback = tb
        
        self._kill(operror)

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
        elif isinstance(thunk, _ResumeThunk):
            raise NotImplementedError
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
        w_flags, w_state, w_thunk, w_parent = space.unpackiterable(w_args,
                                                        expected_length=4)
        self.flags = space.int_w(w_flags)
        if space.is_w(w_parent, space.w_None):
            w_parent = self.w_getmain(space)
        self.parent = space.interp_w(AppCoroutine, w_parent)
        ec = self.space.getexecutioncontext()
        self.subctx.setstate(space, w_state)
        if space.is_w(w_thunk, space.w_None):
            if space.is_w(w_state, space.w_None):
                self.thunk = None
            else:
                self.bind(_ResumeThunk(space, self.costate, self.subctx.topframe))
        else:
            w_func, w_args, w_kwds = space.unpackiterable(w_thunk,
                                                          expected_length=3)
            args = Arguments.frompacked(space, w_args, w_kwds)
            self.bind(_AppThunk(space, self.costate, w_func, args))


# _mixin_ did not work
for methname in StacklessFlags.__dict__:
    meth = getattr(StacklessFlags, methname)
    if hasattr(meth, 'im_func'):
        setattr(AppCoroutine, meth.__name__, meth.im_func)
del meth, methname

def w_get_is_zombie(self, space):
    return space.wrap(self.get_is_zombie())
AppCoroutine.w_get_is_zombie = w_get_is_zombie

def w_get_is_alive(self, space):
    return space.wrap(self.is_alive())
AppCoroutine.w_get_is_alive = w_get_is_alive

def w_descr__framestack(self, space):
    assert isinstance(self, AppCoroutine)
    counter = 0
    f = self.subctx.topframe
    while f is not None:
        counter += 1
        f = f.f_backref()
    items = [None] * counter
    f = self.subctx.topframe
    while f is not None:
        counter -= 1
        assert counter >= 0
        items[counter] = space.wrap(f)
        f = f.f_backref()
    assert counter == 0
    return space.newtuple(items)

def makeStaticMethod(module, classname, funcname):
    "NOT_RPYTHON"
    space = module.space
    w_klass = space.getattr(space.wrap(module), space.wrap(classname))
    # HACK HACK HACK
    # make the typeobject mutable for a while
    from pypy.objspace.std.typeobject import W_TypeObject
    assert isinstance(w_klass, W_TypeObject)
    old_flag = w_klass.flag_heaptype
    w_klass.flag_heaptype = True
    
    space.appexec([w_klass, space.wrap(funcname)], """
        (klass, funcname):
            func = getattr(klass, funcname)
            setattr(klass, funcname, staticmethod(func.im_func))
    """)
    w_klass.flag_heaptype = old_flag

def post_install(module):
    makeStaticMethod(module, 'coroutine', 'getcurrent')
    makeStaticMethod(module, 'coroutine', 'getmain')
    space = module.space
    AppCoroutine._get_state(space).post_install()

# space.appexec("""() :

# maybe use __spacebind__ for postprocessing

AppCoroutine.typedef = TypeDef("coroutine",
    __new__ = interp2app(AppCoroutine.descr_method__new__.im_func),
    bind = interp2app(AppCoroutine.w_bind),
    switch = interp2app(AppCoroutine.w_switch),
    kill = interp2app(AppCoroutine.w_kill),
    throw = interp2app(AppCoroutine.w_throw),
    finished = interp2app(AppCoroutine.w_finished),
    is_alive = GetSetProperty(AppCoroutine.w_get_is_alive),
    is_zombie = GetSetProperty(AppCoroutine.w_get_is_zombie,
      doc=AppCoroutine.get_is_zombie.__doc__), #--- this flag is a bit obscure
      # and not useful (it's totally different from Coroutine.is_zombie(), too)
      # but lib/stackless.py uses it
    _framestack = GetSetProperty(w_descr__framestack),
    getcurrent = interp2app(AppCoroutine.w_getcurrent),
    getmain = interp2app(AppCoroutine.w_getmain),
    __reduce__   = interp2app(AppCoroutine.descr__reduce__),
    __setstate__ = interp2app(AppCoroutine.descr__setstate__),
    __module__ = '_stackless',
)

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.w_tempval = space.w_None
        self.space = space

        # XXX Workaround: for now we need to instantiate these classes
        # explicitly for translation to work
        W_CoroutineExit(space)
        W_TaskletExit(space)

        # Exporting new exception to space
        self.w_CoroutineExit = space.gettypefor(W_CoroutineExit)
        space.setitem(
                      space.exceptions_module.w_dict, 
                      space.new_interned_str('CoroutineExit'), 
                      self.w_CoroutineExit) 
        space.setitem(space.builtin.w_dict, 
                      space.new_interned_str('CoroutineExit'), 
                      self.w_CoroutineExit)
        
        # Should be moved to interp_stackless.py if it's ever implemented...
        self.w_TaskletExit = space.gettypefor(W_TaskletExit)
        space.setitem(
                      space.exceptions_module.w_dict, 
                      space.new_interned_str('TaskletExit'), 
                      self.w_TaskletExit) 
        space.setitem(space.builtin.w_dict, 
                      space.new_interned_str('TaskletExit'), 
                      self.w_TaskletExit)  
        
    def post_install(self):
        self.current = self.main = AppCoroutine(self.space, state=self)
        self.main.subctx.clear_framestack()      # wack

def return_main(space):
    return AppCoroutine._get_state(space).main

def get_stack_depth_limit(space):
    return space.wrap(rstack.get_stack_depth_limit())

@unwrap_spec(limit=int)
def set_stack_depth_limit(space, limit):
    rstack.set_stack_depth_limit(limit)


# ___________________________________________________________________
# unpickling trampoline

def resume_frame(space, w_frame):
    from pypy.interpreter.pyframe import PyFrame
    frame = space.interp_w(PyFrame, w_frame, can_be_None=True)
    w_result = space.w_None
    operr = None
    executioncontext = frame.space.getexecutioncontext()
    while frame is not None:
        code = frame.pycode.co_code
        instr = frame.last_instr
        opcode = ord(code[instr])
        map = pythonopcode.opmap
        call_ops = [map['CALL_FUNCTION'], map['CALL_FUNCTION_KW'], map['CALL_FUNCTION_VAR'], 
                    map['CALL_FUNCTION_VAR_KW'], map['CALL_METHOD']]
        assert opcode in call_ops
        instr += 1
        oparg = ord(code[instr]) | ord(code[instr + 1]) << 8
        nargs = oparg & 0xff
        nkwds = (oparg >> 8) & 0xff
        if space.config.objspace.opcodes.CALL_METHOD and opcode == map['CALL_METHOD']:
            if nkwds == 0:     # only positional arguments
                frame.dropvalues(nargs + 2)
        elif opcode == map['CALL_FUNCTION']:
            if nkwds == 0:     # only positional arguments
                frame.dropvalues(nargs + 1)
        else:
            assert 0

        # small hack: unlink frame out of the execution context, because
        # execute_frame will add it there again
        executioncontext.topframeref = jit.non_virtual_ref(frame.f_backref())
        frame.last_instr = instr + 1 # continue after the call
        try:
            w_result = frame.execute_frame(w_result, operr)
        except OperationError, operr:
            pass
        frame = frame.f_backref()
    return w_result
