from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway

from pypy.objspace.cclp.types import W_Var, W_FailedValue, aliases
from pypy.objspace.cclp.misc import w, v, ClonableCoroutine
from pypy.objspace.cclp.space import W_CSpace
from pypy.objspace.cclp.global_state import scheduler

#-- Singleton scheduler ------------------------------------------------

class Scheduler(object):

    def __init__(self, space):
        self.space = space
        self._main = ClonableCoroutine.w_getcurrent(space)
        self._init_head(self._main)
        self._init_blocked()
        self._switch_count = 0
        # more accounting
        self._per_space_live_threads = {} # space -> nb runnable threads
        self._traced = {} # thread -> vars
        w("MAIN THREAD = ", str(id(self._main)))

    def get_threads(self):
        threads = [self._head]
        curr = self._head._next
        while curr != self._head:
            threads.append(curr)
            curr = curr._next
        return threads

    def _init_blocked(self):
        self._blocked = {} # thread set
        # variables suspension lists
        self._blocked_on = {} # var -> threads
        self._blocked_byneed = {} # var -> threads
        self._asking = {} # thread -> cspace

    def _init_head(self, thread):
        assert isinstance(thread, ClonableCoroutine)
        self._head = thread
        # for the reset case
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
            assert self._head not in self._asking
        except:
            #XXX give sched_info maybe
            raise OperationError(self.space.w_RuntimeError,
                                 self.space.wrap("scheduler is in an incoherent state"))
            
    def _chain_insert(self, thread):
        assert thread._next is thread
        assert thread._prev is thread
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(thread._next, ClonableCoroutine)
        assert isinstance(thread._prev, ClonableCoroutine)
        r = self._head
        l = r._prev
        l._next = thread
        r._prev = thread
        thread._prev = l
        thread._next = r

    def remove_thread(self, thread):
        assert isinstance(thread, ClonableCoroutine)
        w(".. REMOVING", str(id(thread)))
        assert thread not in self._blocked
        del self._traced[thread]
        l = thread._prev
        r = thread._next
        l._next = r
        r._prev = l
        self._head = r
        if r == thread: #XXX write a test for me !
            if not we_are_translated(): 
                import traceback
                traceback.print_exc()
            self.display_head()
        thread._next = thread._prev = None
        # cspace/threads account mgmt
        if thread._cspace is not self.space.w_None:
            count = self.dec_live_thread_count(thread._cspace)
            if count == 0:
                del self._per_space_live_threads[thread._cspace]

    #-- cspace helper

    def is_stable(self, cspace):
        assert isinstance(cspace, W_CSpace)
        if cspace not in self._per_space_live_threads.keys():
            #XXX meaning ?
            return True
        return self._per_space_live_threads[cspace] == 0

    def wait_stable(self, cspace):
        assert isinstance(cspace, W_CSpace)
        if self.is_stable(cspace):
            return
        curr = ClonableCoroutine.w_getcurrent(self.space)
        self._asking[curr] = cspace
        self._blocked[curr] = True
        # either we choose() from inside
        if curr._cspace == cspace:
            self.dec_live_thread_count(cspace)
            self.schedule()
            self.inc_live_thread_count(cspace)
        else: # or we ask() from outside
            self.schedule()

    #-- cspace -> thread_count helpers
    def inc_live_thread_count(self, cspace):
        assert isinstance(cspace, W_CSpace)
        count = self._per_space_live_threads.get(cspace, 0) + 1
        self._per_space_live_threads[cspace]  = count
        return count

    def dec_live_thread_count(self, cspace):
        assert isinstance(cspace, W_CSpace)
        count = self._per_space_live_threads[cspace] -1
        assert count >= 0
        self._per_space_live_threads[cspace] = count 
        return count 
    #-- /

    #-- to be used by logic objspace

    def schedule(self):
        to_be_run = self._select_next()
        assert isinstance(to_be_run, ClonableCoroutine)
        w(".. SWITCHING", str(id(ClonableCoroutine.w_getcurrent(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 

    def schedule_or_pass(self):
        to_be_run = self._select_next(dont_pass=False)
        assert isinstance(to_be_run, ClonableCoroutine)
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
                  or (to_be_run == current):
            
            to_be_run = to_be_run._next
            assert isinstance(to_be_run, ClonableCoroutine)
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
            # asking threads
            if to_be_run in self._asking.keys():
                if self.is_stable(self._asking[to_be_run]):
                    del self._asking[to_be_run]
                    del self._blocked[to_be_run]
                    break
        self._head = to_be_run
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
        if we_are_translated():
            w("<translated: we don't display the head>")
            return
        curr = self._head
        v('Threads : [', '-'.join([str(id(curr)), str(curr in self._blocked)]))
        while curr._next != self._head:
            curr = curr._next
            v('-'.join([str(id(curr)), str(curr in self._blocked)]))
        w(']')

    def add_new_thread(self, thread):
        "insert 'thread' at end of running queue"
        assert isinstance(thread, ClonableCoroutine)
        # cspace account mgmt
        if thread._cspace != self.space.w_None:
            self._per_space_live_threads.get(thread._cspace, 0)
            self.inc_live_thread_count(thread._cspace)
        self._chain_insert(thread)

    def add_to_blocked_on(self, w_var, thread):
        w(".. we BLOCK thread", str(id(thread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var)
        assert isinstance(thread, ClonableCoroutine)
        assert thread not in self._blocked
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
        else:
            blocked = []
            self._blocked_on[w_var] = blocked
        blocked.append(thread)
        self._blocked[thread] = True
        # cspace accounting
        if thread._cspace is not self.space.w_None:
            self.dec_live_thread_count(thread._cspace)

    def unblock_on(self, w_var):
        v(".. we UNBLOCK threads dependants of var", str(w_var))
        assert isinstance(w_var, W_Var)
        blocked = []
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
            del self._blocked_on[w_var]
        w(str([id(thr) for thr in blocked]))
        for thr in blocked:
            del self._blocked[thr]
            # cspace accounting
            if thr._cspace is not self.space.w_None:
                self.inc_live_thread_count(thr._cspace)

    def add_to_blocked_byneed(self, w_var, thread):
        w(".. we BLOCK BYNEED thread", str(id(thread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var)
        assert isinstance(thread, ClonableCoroutine)
        if w_var in self._blocked_byneed:
            blocked = self._blocked_byneed[w_var]
        else:
            blocked = []
            self._blocked_byneed[w_var] = blocked
        blocked.append(thread)
        self._blocked[thread] = True
        # cspace accounting
        if thread._cspace is not self.space.w_None:
            self.dec_live_thread_count(thread._cspace)

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
        for thr in blocked:
            del self._blocked[thr]
            # cspace accounting
            if thr._cspace is not self.space.w_None:
                self.inc_live_thread_count(thr._cspace)
            

    # Logic Variables tracing, helps exception propagation
    # amongst threads
    def trace_vars(self, thread, lvars):
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(lvars, list)
        w(".. TRACING logic vars.", str(lvars), "for", str(id(thread)))
        #assert not self._traced.has_key(thread) doesn't translate 
        self._traced[thread] = lvars

    def dirty_traced_vars(self, thread, failed_value):
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(failed_value, W_FailedValue)
        w(".. DIRTYING traced vars")
        for w_var in self._traced[thread]:
            if self.space.is_true(self.space.is_free(w_var)):
                self.space.bind(w_var, failed_value)


#-- Misc --------------------------------------------------
def reset_scheduler(space):
    "garbage collection of threads might pose some problems"
    scheduler[0] = Scheduler(space)
    scheduler[0]._check_initial_conditions()
app_reset_scheduler = gateway.interp2app(reset_scheduler)

def sched_info(space):
    sched = scheduler[0]
    w_ret = space.newdict([])
    if not we_are_translated(): # XXX and otherwise, WTF ???
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

def sched_all(space):
    s = scheduler[0]
    si = space.setitem
    sw = space.wrap
    w_ret = space.newdict([])
    if not we_are_translated():
        si(w_ret, sw('threads'),
           sw([id(th) for th in s.get_threads()]))
        si(w_ret, sw('blocked_on'),
           sw([(id(var),  [id(th) for th in thl])
               for var, thl in s._blocked_on.items()]))
        si(w_ret, sw('blocked_byneed'),
           sw([(id(var), [id(th) for th in thl])
               for var, thl in s._blocked_byneed.items()]))
        si(w_ret, sw('traced'),
           sw([(id(th), [id(var) for var in lvar])
               for th, lvar in s._traced.items()]))
        si(w_ret, sw('space_accounting'),
           sw([(id(spc), count)
               for spc, count in s._per_space_live_threads.items()]))
        si(w_ret, sw('asking'),
           sw([(id(th), id(spc))
               for th, spc in s._asking.items()]))
    return w_ret
app_sched_all = gateway.interp2app(sched_all)        

def schedule(space):
    "useful til we get preemtive scheduling deep into the vm"
    scheduler[0].schedule_or_pass()
app_schedule = gateway.interp2app(schedule)
