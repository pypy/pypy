from pypy.module._stackless.interp_coroutine import AbstractThunk, BaseCoState, Coroutine
from pypy.module._stackless.interp_clonable import InterpClonableCoroutine

from pypy.rpython.objectmodel import we_are_translated

from pypy.module._stackless.stackless_flags import StacklessFlags
from pypy.interpreter.function import StaticMethod
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError

from pypy.rpython import rstack # for resume points
from pypy.tool import stdlib_opcode as pythonopcode

class ClonableCoroutine(InterpClonableCoroutine): 
    #XXX cut'n'pasted from AppCoroutine
    #    so, watch changes in coroutine.py

    def __init__(self, space, is_main=False):
        self.space = space
        state = self._get_state(space)
        Coroutine.__init__(self, state)
        self.flags = 0
        self.framestack = None
        if not is_main:
             space.getexecutioncontext().subcontext_new(self)
        self._dead = False

    def hello(self):
        if we_are_translated():
            InterpClonableCoroutine.hello(self)
        else:
            ec = self.space.getexecutioncontext()
            ec.subcontext_enter(self)

    def goodbye(self):
        if we_are_translated():
            InterpClonableCoroutine.goodbye(self)
        else:
            ec = self.space.getexecutioncontext()
            ec.subcontext_leave(self)

    def w_getcurrent(space):
        return space.wrap(ClonableCoroutine._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)

    def w_finished(self, w_excinfo):
        """called by AppCoroutine.finish"""
        pass
        
    def is_dead(self):
        return self._dead

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

    def _get_state(space):
        return space.fromcache(AppCoState)
    _get_state = staticmethod(_get_state)


    def descr_method__new__(space, w_subtype):
        co = space.allocate_instance(ClonableCoroutine, w_subtype)
        ClonableCoroutine.__init__(co, space)
        return space.wrap(co)


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
        w_mod    = space.getbuiltinmodule('_stackless')
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
        self.parent = ClonableCoroutine._get_state(space).current
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


def makeStaticMethod(module, classname, funcname):
    space = module.space
    space.appexec(map(space.wrap, (module, classname, funcname)), """
        (module, klassname, funcname):
            klass = getattr(module, klassname)
            func = getattr(klass, funcname)
            setattr(klass, funcname, staticmethod(func.im_func))
    """)

def post_install(module):
    makeStaticMethod(module, 'clonable', 'getcurrent')
    space = module.space
    ClonableCoroutine._get_state(space).post_install()

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.w_tempval = space.w_None
        self.space = space
        
    def post_install(self):
        self.current = self.main = ClonableCoroutine(self.space, is_main=True)

def w_descr__framestack(space, self):
    assert isinstance(self, ClonableCoroutine)
    if self.framestack:
        items = [space.wrap(item) for item in self.framestack.items]
        return space.newtuple(items)
    else:
        return space.newtuple([])

# _mixin_ did not work
for methname in StacklessFlags.__dict__:
    meth = getattr(StacklessFlags, methname)
    if hasattr(meth, 'im_func'):
        setattr(ClonableCoroutine, meth.__name__, meth.im_func)
del meth, methname



ClonableCoroutine.typedef = TypeDef("clonable",
    __new__ = interp2app(ClonableCoroutine.descr_method__new__.im_func),
    _framestack = GetSetProperty(w_descr__framestack),
    getcurrent = interp2app(ClonableCoroutine.w_getcurrent),
    __reduce__   = interp2app(ClonableCoroutine.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(ClonableCoroutine.descr__setstate__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
    __module__ = '_stackless',
)


