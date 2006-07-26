from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError

from pypy.module._stackless.coroutine import _AppThunk
from pypy.module._stackless.coroutine import Coroutine # XXX (type of main coro)
from pypy.module._stackless.interp_clonable import Coroutine, ClonableCoroutine

from pypy.objspace.cclp.types import W_Var, W_Future, W_FailedValue, aliases
from pypy.objspace.cclp.misc import w, v

#-- Singleton scheduler ------------------------------------------------

scheduler = []

class Scheduler(object):

    def __init__(self, space):
        self.space = space
        self._main = ClonableCoroutine.w_getcurrent(space)
        self._init_head(self._main)
        self._init_blocked()
        self._switch_count = 0
        self._traced = {}
        w (".. MAIN THREAD = ", str(id(self._main)))

    def _init_blocked(self):
        self._blocked = {} # thread set
        self._blocked_on = {} # var -> threads
        self._blocked_byneed = {} # var -> threads

    def _init_head(self, coro):
        self._head = coro
        self._head.next = self._head.prev = self._head

    def _set_head(self, thread):
        self._head = thread

    def _check_initial_conditions(self):
        try:
            assert self._head.next == self._head.prev == self._head
            assert self._head not in self._blocked
            assert self._head not in self._blocked_on
            assert self._head not in self._blocked_byneed
        except:
            self.display_head()
            w("BLOCKED", str(self._blocked))
            all = {}
            all.update(self._blocked_on)
            all.update(self._blocked_byneed)
            w(str(all))
            raise
            
    def _chain_insert(self, thread):
        assert thread.next is None
        assert thread.prev is None
        if self._head is None:
            thread.next = thread
            thread.prev = thread
            self._set_head(thread)
        else:
            r = self._head
            l = r.prev
            l.next = thread
            r.prev = thread
            thread.prev = l
            thread.next = r

    def remove_thread(self, thread):
        #XXX don't we need to notify the consumers ?
        w(".. REMOVING", str(id(thread)))
        assert thread not in self._blocked
        del self._traced[thread]
        l = thread.prev
        r = thread.next
        l.next = r
        r.prev = l
        if r == thread:
            w("DUH !")
            self.display_head()
        thread.next = thread.next = None
        return thread

    #-- to be used by logic objspace

    def schedule(self):
        to_be_run = self._select_next()
        w(".. SWITCHING", str(id(ClonableCoroutine.w_getcurrent(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 

    def schedule_or_pass(self):
        to_be_run = self._select_next(dont_pass=False)
        curr = ClonableCoroutine.w_getcurrent(self.space)
        if to_be_run == curr:
            w(".. PASS")
            return
        w(".. SWITCHING", str(id(curr)), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 
        
    def _select_next(self, dont_pass=True):
        to_be_run = self._head
        sentinel = to_be_run
        current = ClonableCoroutine.w_getcurrent(self.space)
        while (to_be_run in self._blocked) \
                  or to_be_run.is_dead() \
                  or (dont_pass and (to_be_run == current)):
            to_be_run = to_be_run.next
            if to_be_run == sentinel:
                self.display_head()
                ## we RESET sched state so as to keep being usable beyond that
                self._init_head(self._main)
                self._init_blocked()
                w(".. SCHEDULER reinitialized")
                raise OperationError(self.space.w_RuntimeError,
                                     self.space.wrap("can't schedule, possible deadlock in sight"))
        return to_be_run

    #XXX call me directly for this to work translated
    def __len__(self):
        "count of known threads (including dead ones)"
        curr = self._head
        sentinel = curr
        count = 1 # there is always a main thread
        while curr.next != sentinel:
            curr = curr.next
            count += 1
        return count

    def display_head(self):
        curr = self._head
        v('Threads : [', '-'.join([str(id(curr)), str(curr in self._blocked)]))
        while curr.next != self._head:
            curr = curr.next
            v('-'.join([str(id(curr)), str(curr in self._blocked)]))
        w(']')

    def add_new_thread(self, thread):
        "insert 'thread' at end of running queue"
        assert isinstance(thread, ClonableCoroutine)
        self._chain_insert(thread)

    def add_to_blocked_on(self, w_var, uthread):
        w(".. we BLOCK thread", str(id(uthread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var)
        assert isinstance(uthread, Coroutine)
        assert uthread not in self._blocked
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
        else:
            blocked = []
            self._blocked_on[w_var] = blocked
        blocked.append(uthread)
        self._blocked[uthread] = True

    def unblock_on(self, w_var):
        v(".. we UNBLOCK threads dependants of var", str(w_var))
        assert isinstance(w_var, W_Var)
        blocked = []
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
            del self._blocked_on[w_var]
        w(str([id(thr) for thr in blocked]))
        for thr in blocked: del self._blocked[thr]

    def add_to_blocked_byneed(self, w_var, uthread):
        w(".. we BLOCK BYNEED thread", str(id(uthread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var)
        assert isinstance(uthread, ClonableCoroutine)
        if w_var in self._blocked_byneed:
            blocked = self._blocked_byneed[w_var]
        else:
            blocked = []
            self._blocked_byneed[w_var] = blocked
        blocked.append(uthread)
        self._blocked[uthread] = True

    def unblock_byneed_on(self, w_var):
        v(".. we UNBLOCK BYNEED dependants of var", str(w_var))
        assert isinstance(w_var, W_Var)
        blocked = []
        for w_alias in aliases(self.space, w_var):
            if w_alias in self._blocked_byneed:
                blocked += self._blocked_byneed[w_alias]
                del self._blocked_byneed[w_alias]
            w_alias.needed = True
        w(str([id(thr) for thr in blocked]))
        for thr in blocked: del self._blocked[thr]

    def trace_vars(self, thread, lvars):
        assert isinstance(thread, Coroutine)
        assert isinstance(lvars, list)
        w(".. TRACING logic vars.", str(lvars), "for", str(id(thread)))
        #assert not self._traced.has_key(thread) doesn't translate 
        self._traced[thread] = lvars

    def dirty_traced_vars(self, thread, failed_value):
        w(".. DIRTYING traced vars")
        for w_var in self._traced[thread]:
            if self.space.is_true(self.space.is_free(w_var)):
                self.space.bind(w_var, failed_value)


#-- Thunk -----------------------------------------

class FutureThunk(_AppThunk):
    def __init__(self, space, w_callable, args, w_Result, coro):
        _AppThunk.__init__(self, space, coro.costate, w_callable, args)
        self.w_Result = w_Result 
        self._coro = coro

    def call(self):
        w(".. initial thunk CALL in", str(id(self._coro)))
        scheduler[0].trace_vars(self._coro, logic_args(self.args.unpack()))
        try:
            try:
                _AppThunk.call(self)
            except Exception, exc:
                w(".. exceptional EXIT of", str(id(self._coro)), "with", str(exc))
                failed_val = W_FailedValue(exc)
                self.space.bind(self.w_Result, failed_val)
                scheduler[0].dirty_traced_vars(self._coro, failed_val)
                self._coro._dead = True
            else:
                w(".. clean EXIT of", str(id(self._coro)),
                  "-- setting future result", str(self.w_Result), "to",
                  str(self.costate.w_tempval))
                self.space.unify(self.w_Result, self.costate.w_tempval)
        finally:
            scheduler[0].remove_thread(self._coro)
            scheduler[0].schedule()


def logic_args(args):
    "returns logic vars found in unpacked normalized args"
    assert isinstance(args, tuple)
    pos = args[0]
    kwa = args[1]
    pos_l = [arg for arg in pos
             if isinstance(arg, W_Var)]
    kwa_l = [arg for arg in kwa.keys()
             if isinstance(arg, W_Var)]
    return pos_l + kwa_l


#-- Future --------------------------------------------------

def future(space, w_callable, __args__):
    """returns a future result"""
    args = __args__.normalize()
    # coro init
    coro = ClonableCoroutine(space)
    # prepare thread chaining, create missing slots
    coro.next = coro.prev = None
    # feed the coro
    w_Future = W_Future(space)
    thunk = FutureThunk(space, w_callable, args, w_Future, coro)
    coro.bind(thunk)
    w("THREAD", str(id(coro)))
    scheduler[0].add_new_thread(coro)
    # XXX we should think about a way to make it read-only for the client
    #     (i.e the originator), aka true futures
    return w_Future
app_future = gateway.interp2app(future, unwrap_spec=[baseobjspace.ObjSpace,
                                                     baseobjspace.W_Root,
                                                     argument.Arguments])
    
# need (applevel) : getcurrent(), getmain(), 

#-- Misc --------------------------------------------------

def sched_stats(space):
    sched = scheduler[0]
    w_ret = space.newdict([])
    space.setitem(w_ret, space.wrap('switches'), space.wrap(sched._switch_count))
    space.setitem(w_ret, space.wrap('threads'), space.wrap(sched.__len__()))
    space.setitem(w_ret, space.wrap('blocked'), space.wrap(len(sched._blocked)))
    space.setitem(w_ret, space.wrap('blocked_on'), space.wrap(len(sched._blocked_on)))
    space.setitem(w_ret, space.wrap('blocked_byneed'), space.wrap(len(sched._blocked_byneed)))
    return w_ret
app_sched_stats = gateway.interp2app(sched_stats)


def schedule(space):
    "useful til we get preemtive scheduling deep into the vm"
    scheduler[0].schedule_or_pass()
app_schedule = gateway.interp2app(schedule)

