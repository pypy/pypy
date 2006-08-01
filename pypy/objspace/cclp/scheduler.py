from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway

from pypy.objspace.cclp.types import W_Var, aliases
from pypy.objspace.cclp.misc import w, v, ClonableCoroutine
from pypy.objspace.cclp.space import CSpace

scheduler = []

#-- Singleton scheduler ------------------------------------------------

class Scheduler(object):

    def __init__(self, space):
        self.space = space
        self._main = ClonableCoroutine.w_getcurrent(space)
        # link top_level space to main coroutine
        self.top_space = CSpace(space, self._main)
        self._main.cspace = self.top_space
        # ...
        self._init_head(self._main)
        self._init_blocked()
        self._switch_count = 0
        self._traced = {}
        w (".. MAIN THREAD = ", str(id(self._main)))

    def get_threads(self):
        threads = [self._head]
        curr = self._head._next
        while curr != self._head:
            threads.append(curr)
            curr = curr._next
        return threads

    def _init_blocked(self):
        self._blocked = {} # thread set
        self._blocked_on = {} # var -> threads
        self._blocked_byneed = {} # var -> threads

    def _init_head(self, coro):
        self._head = coro
        self._head._next = self._head._prev = self._head

    def _set_head(self, thread):
        assert isinstance(thread, ClonableCoroutine)
        self._head = thread

    def _check_initial_conditions(self):
        try:
            assert self._head._next == self._head._prev == self._head
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
        assert thread._next is thread
        assert thread._prev is thread
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(thread._next, ClonableCoroutine)
        assert isinstance(thread._prev, ClonableCoroutine)
        if self._head is None:
            thread._next = thread
            thread._prev = thread
            self._set_head(thread)
        else:
            r = self._head
            l = r._prev
            l._next = thread
            r._prev = thread
            thread._prev = l
            thread._next = r

    def remove_thread(self, thread):
        w(".. REMOVING", str(id(thread)))
        assert thread not in self._blocked
        del self._traced[thread]
        l = thread._prev
        r = thread._next
        l._next = r
        r._prev = l
        if r == thread: #XXX write a test for me !
            if not we_are_translated(): 
                import traceback
                traceback.print_exc()
            self.display_head()
        thread._next = thread._next = None
        return thread

    #-- to be used by logic objspace

    def schedule(self):
        to_be_run = self._select_next()
        w(".. SWITCHING", str(id(ClonableCoroutine.w_getcurrent(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        assert isinstance(to_be_run, ClonableCoroutine)
        to_be_run.w_switch() 

    def schedule_or_pass(self):
        to_be_run = self._select_next(dont_pass=False)
        curr = ClonableCoroutine.w_getcurrent(self.space)
        if to_be_run == curr:
            w(".. PASS")
            return
        w(".. SWITCHING", str(id(curr)), "=>", str(id(to_be_run)))
        self._switch_count += 1
        assert isinstance(to_be_run, ClonableCoroutine)
        to_be_run.w_switch() 
        
    def _select_next(self, dont_pass=True):
        to_be_run = self._head
        sentinel = to_be_run
        current = ClonableCoroutine.w_getcurrent(self.space)
        while (to_be_run in self._blocked) \
                  or to_be_run.is_dead() \
                  or (to_be_run == current):
            to_be_run = to_be_run._next
            if to_be_run == sentinel:
                if not dont_pass:
                    return ClonableCoroutine.w_getcurrent(self.space)
                self.display_head()
                ## we RESET sched state so as to keep being usable beyond that
                self._init_head(self._main)
                self._init_blocked()
                w(".. SCHEDULER reinitialized")
                raise OperationError(self.space.w_AllBlockedError,
                                     self.space.wrap("can't schedule, possible deadlock in sight"))
        return to_be_run

    #XXX call me directly for this to work translated
    def __len__(self):
        "count of known threads (including dead ones)"
        curr = self._head
        sentinel = curr
        count = 1 # there is always a main thread
        while curr._next != sentinel:
            curr = curr._next
            count += 1
        return count

    def display_head(self):
        curr = self._head
        v('Threads : [', '-'.join([str(id(curr)), str(curr in self._blocked)]))
        while curr._next != self._head:
            curr = curr._next
            v('-'.join([str(id(curr)), str(curr in self._blocked)]))
        w(']')

    def add_new_thread(self, thread):
        "insert 'thread' at end of running queue"
        assert isinstance(thread, ClonableCoroutine)
        self._chain_insert(thread)

    def add_to_blocked_on(self, w_var, uthread):
        w(".. we BLOCK thread", str(id(uthread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var)
        assert isinstance(uthread, ClonableCoroutine)
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

    # Logic Variables tracing, helps exception propagation
    # amongst threads
    def trace_vars(self, thread, lvars):
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(lvars, list)
        w(".. TRACING logic vars.", str(lvars), "for", str(id(thread)))
        #assert not self._traced.has_key(thread) doesn't translate 
        self._traced[thread] = lvars

    def dirty_traced_vars(self, thread, failed_value):
        w(".. DIRTYING traced vars")
        for w_var in self._traced[thread]:
            if self.space.is_true(self.space.is_free(w_var)):
                self.space.bind(w_var, failed_value)


#-- Misc --------------------------------------------------
def reset_scheduler(space):
    "garbage collection of threads might pose some problems"
    scheduler[0] = Scheduler(space)
app_reset_scheduler = gateway.interp2app(reset_scheduler)

def sched_info(space):
    sched = scheduler[0]
    w_ret = space.newdict([])
    space.setitem(w_ret, space.wrap('switches'), space.wrap(sched._switch_count))
    space.setitem(w_ret, space.wrap('threads'),
                  space.wrap([id(th) for th in sched.get_threads()]))
    space.setitem(w_ret, space.wrap('blocked'),
                  space.wrap([id(th) for th in sched._blocked.keys()]))
    space.setitem(w_ret, space.wrap('blocked_on'),
                  space.wrap([id(th) for th in sched._blocked_on.keys()]))
    space.setitem(w_ret, space.wrap('blocked_byneed'),
                  space.wrap([id(th) for th in sched._blocked_byneed.keys()]))
    return w_ret
app_sched_info = gateway.interp2app(sched_info)


def schedule(space):
    "useful til we get preemtive scheduling deep into the vm"
    scheduler[0].schedule_or_pass()
app_schedule = gateway.interp2app(schedule)
