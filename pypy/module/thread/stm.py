"""
Software Transactional Memory emulation of the GIL.
"""

from pypy.module.thread.threadlocals import BaseThreadLocals
from pypy.module.thread.error import wrap_thread_error
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.gateway import W_Root, interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, descr_get_dict
from rpython.rlib import rthread
from rpython.rlib import rstm
from rpython.rlib import jit
from rpython.rlib.objectmodel import invoke_around_extcall, we_are_translated


class FakeWeakKeyDictionary:
    # Only used if we don't have weakrefs.
    # Then thread._local instances will leak, but too bad.
    def __init__(self):
        self.d = {}
    def get(self, key):
        return self.d.get(key, None)
    def set(self, key, value):
        self.d[key] = value


ec_cache = rstm.ThreadLocalReference(ExecutionContext)

def initialize_execution_context(ec):
    """Called from ExecutionContext.__init__()."""
    if ec.space.config.translation.rweakref:
        from rpython.rlib import rweakref
        ec._thread_local_dicts = rweakref.RWeakKeyDictionary(STMLocal, W_Root)
    else:
        ec._thread_local_dicts = FakeWeakKeyDictionary()
    if ec.space.config.objspace.std.withmethodcache:
        from pypy.objspace.std.typeobject import MethodCache
        ec._methodcache = MethodCache(ec.space)

def _fill_untranslated(ec):
    if not we_are_translated() and not hasattr(ec, '_thread_local_dicts'):
        initialize_execution_context(ec)


class STMThreadLocals(BaseThreadLocals):

    def initialize(self, space):
        """NOT_RPYTHON: set up a mechanism to send to the C code the value
        set by space.actionflag.setcheckinterval()."""
        #
        def setcheckinterval_callback():
            self.configure_transaction_length(space)
        #
        assert space.actionflag.setcheckinterval_callback is None
        space.actionflag.setcheckinterval_callback = setcheckinterval_callback
        self.threads_running = False
        self.seen_main_ec = False

    def getvalue(self):
        return ec_cache.get()

    def setvalue(self, value):
        if not self.seen_main_ec and value is not None:
            value._signals_enabled = 1    # the main thread is enabled
            self._mainthreadident = rthread.get_ident()
            self.seen_main_ec = True
        ec_cache.set(value)

    def getallvalues(self):
        raise ValueError

    def leave_thread(self, space):
        self.setvalue(None)

    def setup_threads(self, space):
        self.threads_running = True
        self.configure_transaction_length(space)
        invoke_around_extcall(rstm.before_external_call,
                              rstm.after_external_call,
                              rstm.enter_callback_call,
                              rstm.leave_callback_call)

    def reinit_threads(self, space):
        self.setup_threads(space)
        ident = rthread.get_ident()
        if ident != self._mainthreadident:
            ec = self.getvalue()
            ec._signals_enabled += 1
            self._mainthreadident = ident

    def configure_transaction_length(self, space):
        if self.threads_running:
            interval = space.actionflag.getcheckinterval()
            rstm.set_transaction_length(interval / 10000.0)

# ____________________________________________________________


class STMLock(rthread.Lock):
    def __init__(self, space, ll_lock):
        rthread.Lock.__init__(self, ll_lock)
        self.space = space

    def acquire(self, flag):
        if rstm.is_atomic():
            acquired = rthread.Lock.acquire(self, False)
            if flag and not acquired:
                raise wrap_thread_error(self.space,
                    "deadlock: an atomic transaction tries to acquire "
                    "a lock that is already acquired.  See pypy/doc/stm.rst.")
        else:
            acquired = rthread.Lock.acquire(self, flag)
        return acquired

def allocate_stm_lock(space):
    return STMLock(space, rthread.allocate_ll_lock())

# ____________________________________________________________


class STMLocal(W_Root):
    """Thread-local data"""

    @jit.dont_look_inside
    def __init__(self, space, initargs):
        self.space = space
        self.initargs = initargs
        # The app-level __init__() will be called by the general
        # instance-creation logic.  It causes getdict() to be
        # immediately called.  If we don't prepare and set a w_dict
        # for the current thread, then this would in cause getdict()
        # to call __init__() a second time.
        ec = space.getexecutioncontext()
        _fill_untranslated(ec)
        w_dict = space.newdict(instance=True)
        ec._thread_local_dicts.set(self, w_dict)

    @jit.dont_look_inside
    def create_new_dict(self, ec):
        # create a new dict for this thread
        space = self.space
        w_dict = space.newdict(instance=True)
        ec._thread_local_dicts.set(self, w_dict)
        # call __init__
        try:
            w_self = space.wrap(self)
            w_type = space.type(w_self)
            w_init = space.getattr(w_type, space.wrap("__init__"))
            space.call_obj_args(w_init, w_self, self.initargs)
        except:
            # failed, forget w_dict and propagate the exception
            ec._thread_local_dicts.set(self, None)
            raise
        # ready
        return w_dict

    def getdict(self, space):
        ec = space.getexecutioncontext()
        _fill_untranslated(ec)
        w_dict = ec._thread_local_dicts.get(self)
        if w_dict is None:
            w_dict = self.create_new_dict(ec)
        return w_dict

    def descr_local__new__(space, w_subtype, __args__):
        local = space.allocate_instance(STMLocal, w_subtype)
        STMLocal.__init__(local, space, __args__)
        return space.wrap(local)

    def descr_local__init__(self, space):
        # No arguments allowed
        pass

STMLocal.typedef = TypeDef("thread._local",
                     __doc__ = "Thread-local data",
                     __new__ = interp2app(STMLocal.descr_local__new__.im_func),
                     __init__ = interp2app(STMLocal.descr_local__init__),
                     __dict__ = GetSetProperty(descr_get_dict, cls=STMLocal),
                     )
