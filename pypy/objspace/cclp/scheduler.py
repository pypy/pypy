from pypy.rpython.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.objspace.std.listobject import W_ListObject

from pypy.objspace.cclp.types import W_Var, W_FailedValue, aliases
from pypy.objspace.cclp.misc import w, v, ClonableCoroutine
from pypy.objspace.cclp.space import W_CSpace
from pypy.objspace.cclp.global_state import sched

#-- Singleton scheduler ------------------------------------------------

class Scheduler(object):

    def __init__(self, space):
        self.space = space
        self._main = ClonableCoroutine.w_getcurrent(space)
        assert isinstance(self._main, ClonableCoroutine)
        self._switch_count = 0
        self._init_head(self._main)
        self._blocked = {} # thread set
        # variables suspension lists
        self._blocked_on = {} # var -> threads
        self._blocked_byneed = {} # var -> threads
        self._asking = {} # thread -> cspace
        # more accounting
        self._per_space_live_threads = {} # space -> nb runnable threads
        self._traced = {} # thread -> vars
        w("MAIN THREAD = ", str(id(self._main)))

    def _init_head(self, thread):
        assert isinstance(thread, ClonableCoroutine)
        self._head = thread
        # for the reset case
        self._head._next = self._head._prev = self._head
            
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
        assert isinstance(curr, ClonableCoroutine)
        self._asking[curr] = cspace
        self._blocked[curr] = True
        # either we choose() from inside
        if curr._cspace == cspace:
            self.dec_live_thread_count(cspace)
            self.schedule()
            self.inc_live_thread_count(cspace)
        else: # or we ask(), or clone() from outside
            self.schedule()

    #-- cspace -> thread_count helpers
    
    def inc_live_thread_count(self, cspace):
        assert isinstance(cspace, W_CSpace)
        count = self._per_space_live_threads.get(cspace, 0) + 1
        self._per_space_live_threads[cspace]  = count
        return count

    def dec_live_thread_count(self, cspace):
        assert isinstance(cspace, W_CSpace)
        count = self._per_space_live_threads[cspace] - 1
        assert count >= 0
        self._per_space_live_threads[cspace] = count
        return count 
    #-- /

    #-- to be used by logic objspace

    def schedule(self):
        to_be_run = self._select_next()
        assert isinstance(to_be_run, ClonableCoroutine)
        #w(".. SWITCHING", str(id(ClonableCoroutine.w_getcurrent(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 

    def schedule_or_pass(self):
        to_be_run = self._select_next(dont_pass=False)
        assert isinstance(to_be_run, ClonableCoroutine)
        curr = ClonableCoroutine.w_getcurrent(self.space)
        if to_be_run == curr:
            w(".. PASS")
            return
        #w(".. SWITCHING", str(id(curr)), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 
        
    def _select_next(self, dont_pass=True):
        to_be_run = self._head
        sentinel = to_be_run
        current = ClonableCoroutine.w_getcurrent(self.space)
        assert isinstance(current, ClonableCoroutine)
        while (to_be_run in self._blocked) \
                  or (to_be_run == current):
            
            to_be_run = to_be_run._next
            assert isinstance(to_be_run, ClonableCoroutine)
            # asking threads
            if to_be_run in self._asking:
                if self.is_stable(self._asking[to_be_run]):
                    del self._asking[to_be_run]
                    del self._blocked[to_be_run]
                    break
            if to_be_run == sentinel:
                if not dont_pass:
                    return current
                w(str(sched_info(self.space)))
                ## we RESET sched state so as to keep being usable beyond that
                reset_scheduler(self.space)
                sched.uler._main = sched.uler._head = self._head
                w(".. SCHEDULER reinitialized")
                raise OperationError(self.space.w_AllBlockedError,
                                     self.space.wrap("can't schedule, probable deadlock in sight"))
        self._head = to_be_run
        return to_be_run

    def add_new_thread(self, thread):
        "insert 'thread' at end of running queue"
        assert isinstance(thread, ClonableCoroutine)
        # cspace account mgmt
        if thread._cspace is not None:
            self._per_space_live_threads.get(thread._cspace, 0)
            self.inc_live_thread_count(thread._cspace)
        self._chain_insert(thread)

    def remove_thread(self, thread):
        assert isinstance(thread, ClonableCoroutine)
        w(".. REMOVING", str(id(thread)))
        assert thread not in self._blocked
        try:
            del self._traced[thread]
        except KeyError:
            pass
            #w(".. removing non-traced thread")
        l = thread._prev
        r = thread._next
        l._next = r
        r._prev = l
        self._head = r
        if r == thread: #XXX write a test for me !
            if not we_are_translated():
                import traceback
                traceback.print_exc()
        thread._next = thread._prev = None
        # cspace/threads account mgmt
        if thread._cspace is not None:
            cspace = thread._cspace
            live = self.dec_live_thread_count(cspace)
            if live == 0:
                del self._per_space_live_threads[cspace]

    def add_to_blocked_on(self, w_var, thread):
        #w(".. we BLOCK thread", str(id(thread)), "on var", str(w_var))
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
        if thread._cspace is not None:
            self.dec_live_thread_count(thread._cspace)

    def unblock_on(self, w_var):
        #v(".. we UNBLOCK threads dependants of var", str(w_var))
        assert isinstance(w_var, W_Var)
        blocked = []
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
            del self._blocked_on[w_var]
        #w(str([id(thr) for thr in blocked]))
        for thr in blocked:
            del self._blocked[thr]
            # cspace accounting
            if thr._cspace is not None:
                self.inc_live_thread_count(thr._cspace)

    def add_to_blocked_byneed(self, w_var, thread):
        #w(".. we BLOCK BYNEED thread", str(id(thread)), "on var", str(w_var))
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
        if thread._cspace is not None:
            self.dec_live_thread_count(thread._cspace)

    def unblock_byneed_on(self, w_var):
        #v(".. we UNBLOCK BYNEED dependants of var", str(w_var))
        assert isinstance(w_var, W_Var)
        blocked = []
        for w_alias in aliases(self.space, w_var):
            if w_alias in self._blocked_byneed:
                blocked += self._blocked_byneed[w_alias]
                del self._blocked_byneed[w_alias]
            w_alias.needed = True
        #w(str([id(thr) for thr in blocked]))
        for thr in blocked:
            del self._blocked[thr]
            # cspace accounting
            if thr._cspace is not None:
                self.inc_live_thread_count(thr._cspace)
            

    # Logic Variables tracing, helps exception propagation
    # amongst threads
    def trace_vars(self, thread, lvars):
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(lvars, list)
        #w(".. TRACING logic vars.", str(lvars), "for", str(id(thread)))
        #assert not self._traced.has_key(thread) doesn't translate 
        self._traced[thread] = lvars

    def dirty_traced_vars(self, thread, failed_value):
        assert isinstance(thread, ClonableCoroutine)
        assert isinstance(failed_value, W_FailedValue)
        #w(".. DIRTYING traced vars")
        for w_var in self._traced[thread]:
            if self.space.is_true(self.space.is_free(w_var)):
                self.space.bind(w_var, failed_value)

    def w_threads(self):
        s = self.space
        thl = [s.newint(id(self._head))]
        assert isinstance(self._head, ClonableCoroutine)
        curr = self._head._next
        while curr != self._head:
            assert isinstance(curr, ClonableCoroutine)
            thl.append(s.newint(id(curr)))
            curr = curr._next
        w_t = W_ListObject(thl)
        return w_t

    def w_blocked(self):
        s = self.space
        w_b = W_ListObject([s.newint(id(th))
                            for th in self._blocked.keys()])
        return w_b

    def w_blocked_on(self):
        s = self.space
        si = s.setitem
        w_bo = s.newdict()
        for var, thl in self._blocked_on.items():
            w_l = W_ListObject([s.newint(id(th))
                                for th in thl])
            si(w_bo, s.wrap(str(var)), w_l)
        return w_bo

    def w_blocked_byneed(self):
        s = self.space
        si = s.setitem
        w_bb = s.newdict()
        for var, thl in self._blocked_byneed.items():
            w_l = W_ListObject([s.newint(id(th))
                                for th in thl])
            si(w_bb, s.wrap(str(var)), w_l)
        return w_bb

    def w_space_accounting(self):
        s = self.space
        si = s.setitem
        w_a = s.newdict()
        for sp, thc in self._per_space_live_threads.items():
            si(w_a, s.newint(id(sp)), s.newint(thc))
        return w_a

    def w_asking(self):
        s = self.space
        si = s.setitem
        w_a = s.newdict()
        for th, sp in self._asking.items():
            si(w_a, s.newint(id(th)), s.newint(id(sp)))
        return w_a

        
#-- Misc --------------------------------------------------
def reset_scheduler(space):
    sched.uler = Scheduler(space)
app_reset_scheduler = gateway.interp2app(reset_scheduler)

def sched_info(space):
    s = sched.uler
    si = space.setitem
    sw = space.wrap
    w_ret = space.newdict()
    si(w_ret, sw('switches'), space.newint(s._switch_count))
    si(w_ret, sw('threads'), s.w_threads())
    si(w_ret, sw('blocked'), s.w_blocked())
    si(w_ret, sw('blocked_on'), s.w_blocked_on())
    si(w_ret, sw('blocked_byneed'), s.w_blocked_byneed())
    si(w_ret, sw('space_accounting'), s.w_space_accounting())
    si(w_ret, sw('asking'), s.w_asking())
    return w_ret
app_sched_info = gateway.interp2app(sched_info)        

def schedule(space):
    "useful til we get preemtive scheduling deep into the vm"
    sched.uler.schedule_or_pass()
app_schedule = gateway.interp2app(schedule)
