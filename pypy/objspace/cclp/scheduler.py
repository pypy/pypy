from pypy.rlib.objectmodel import we_are_translated
from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway, baseobjspace
from pypy.objspace.std.listobject import W_ListObject

from pypy.objspace.cclp.types import W_Var, W_FailedValue, aliases
from pypy.objspace.cclp.misc import w, v, AppCoroutine, get_current_cspace
from pypy.objspace.cclp.global_state import sched

#-- Singleton scheduler ------------------------------------------------

class TopLevelScheduler(object):

    # we are dealing with cspaces

    def __init__(self, space, top_level_space):
        w("NEW TOPLEVEL SCHEDULER", str(id(self)), "with", str(id(top_level_space)))
        self.space = space
        sched.main_thread._cspace = top_level_space
        self._switch_count = 0
        self._head = top_level_space
        self._head._next = self._head._prev = self._head
        # asking for stability
        self._asking = {} # cspace -> thread set
        self._asking[top_level_space] = {} # XXX
        # variables suspension lists
        self._blocked = {}
        self._blocked_on = {} # var -> threads
        self._blocked_byneed = {} # var -> threads
        
    def _chain_insert(self, group):
        assert group._next is group, "group._next not correctly linked"
        assert group._prev is group, "group._prev not correctly linked"
        assert isinstance(group, W_ThreadGroupScheduler), "type error"
        assert isinstance(group._next, W_ThreadGroupScheduler), "type error"
        assert isinstance(group._prev, W_ThreadGroupScheduler), "type error"
        r = self._head
        l = r._prev
        l._next = group
        r._prev = group
        group._prev = l
        group._next = r


    def schedule(self):
        running = self._head
        to_be_run = self._select_next()
        assert isinstance(to_be_run, W_ThreadGroupScheduler), "type error"
        #w(".. SWITCHING (spaces)", str(id(get_current_cspace(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        if to_be_run != running:
            if running._pool is not None:
                running.goodbye()
            if to_be_run._pool is not None:
                to_be_run.hello()
        to_be_run.schedule() 

    def _select_next(self):
        to_be_run = self._head
        sentinel = to_be_run
        while to_be_run.is_blocked():
            # check stability + asking status, give a chance to run
            if to_be_run.is_runnable():
                break
            to_be_run = to_be_run._next
            assert isinstance(to_be_run, W_ThreadGroupScheduler), "type error"
            if to_be_run == sentinel:
                reset_scheduler(self.space)
                w(".. SCHEDULER reinitialized")
                raise OperationError(self.space.w_AllBlockedError,
                                     self.space.wrap("can't schedule, probable deadlock in sight"))
        self._head = to_be_run
        return to_be_run


    def add_new_group(self, group):
        "insert 'group' at end of running queue"
        assert isinstance(group, W_ThreadGroupScheduler), "type error"
        w(".. ADDING group", str(id(group)))
        self._asking[group] = {}
        self._chain_insert(group)

    def remove_group(self, group):
        assert isinstance(group, W_ThreadGroupScheduler), "type error"
        w(".. REMOVING group", str(id(group)))
        l = group._prev
        r = group._next
        l._next = r
        r._prev = l
        self._head = r
        if r == group:
            # IS AN ERROR
            if not we_are_translated():
                import traceback
                traceback.print_exc()
        group._next = group._prev = None
        # unblock all threads asking stability of this group
        for th in self._asking[group]:
            del self._blocked[th]
            th._cspace.blocked_count -= 1
        del self._asking[group]


    def add_to_blocked_on(self, w_var, thread):
        w(".. we BLOCK thread", str(id(thread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var), "type error"
        assert isinstance(thread, AppCoroutine), "type error"
        assert thread not in self._blocked
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
        else:
            blocked = []
            self._blocked_on[w_var] = blocked
        blocked.append(thread)
        self._blocked[thread] = True
        # stability, accounting, etc
        self._post_blocking(thread)

            
    def unblock_on(self, w_var):
        v(".. we UNBLOCK threads dependants of var", str(w_var))
        assert isinstance(w_var, W_Var), "type error"
        blocked = []
        if w_var in self._blocked_on:
            blocked = self._blocked_on[w_var]
            del self._blocked_on[w_var]
        w(str([id(thr) for thr in blocked]))
        for thr in blocked:
            del self._blocked[thr]
            thr._cspace.blocked_count -= 1

    #XXX sync the un/block byneed stuff with above, later
    def add_to_blocked_byneed(self, w_var, thread):
        w(".. we BLOCK BYNEED thread", str(id(thread)), "on var", str(w_var))
        assert isinstance(w_var, W_Var), "type error"
        assert isinstance(thread, AppCoroutine), "type error"
        if w_var in self._blocked_byneed:
            blocked = self._blocked_byneed[w_var]
        else:
            blocked = []
            self._blocked_byneed[w_var] = blocked
        blocked.append(thread)
        self._blocked[thread] = True
        self._post_blocking(thread)

    def unblock_byneed_on(self, w_var):
        v(".. we UNBLOCK BYNEED dependants of var", str(w_var))
        assert isinstance(w_var, W_Var), "type error"
        blocked = []
        for w_alias in aliases(self.space, w_var):
            if w_alias in self._blocked_byneed:
                blocked += self._blocked_byneed[w_alias]
                del self._blocked_byneed[w_alias]
            w_alias.needed = True
        w(str([id(thr) for thr in blocked]))
        for thr in blocked:
            del self._blocked[thr]
            thr._cspace.blocked_count -= 1

    def _post_blocking(self, thread):
        # check that those asking for stability in the home space
        # of the thread can be unblocked
        home = thread._cspace
        home.blocked_count += 1
        if home.is_stable():
            for th in sched.uler._asking[home].keys():
                # these asking threads must be unblocked, in their
                # respective home spaces
                del sched.uler._blocked[th]
                th._cspace.blocked_count -= 1
            sched.uler._asking[home] = {}

    # delegated to thread group
    def add_new_thread(self, thread):
        tg = get_current_cspace(self.space)
        tg.add_new_thread(thread)

    def remove_thread(self, thread):
        tg = get_current_cspace(self.space)
        tg.remove_thread(thread)

    def trace_vars(self, thread, lvars):
        tg = get_current_cspace(self.space)
        tg.trace_vars(thread, lvars)

    def dirty_traced_vars(self, thread, failed_value):
        tg = get_current_cspace(self.space)
        tg.dirty_traced_vars(thread, failed_value)

    def wait_stable(self):
        tg = get_current_cspace(self.space)
        tg.wait_stable()

    # statistics
    def sched_info(self):
        s = self.space
        si = self.space.setitem
        w_all = s.newdict()
        si(w_all, s.newint(id(self._head)), self._head.group_info())
        assert isinstance(self._head, W_ThreadGroupScheduler), "type error"
        curr = self._head._next
        while curr != self._head:
            assert isinstance(curr, W_ThreadGroupScheduler), "type error"
            si(w_all, s.newint(id(curr)), curr.group_info())
            curr = curr._next
        si(w_all, s.wrap('blocked'), self.w_blocked())
        si(w_all, s.wrap('blocked_on'), self.w_blocked_on())
        si(w_all, s.wrap('blocked_byneed'), self.w_blocked_byneed())
        return w_all
        
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


#-- Thread Group scheduler --------------------------------------


class W_ThreadGroupScheduler(baseobjspace.Wrappable):

    def __init__(self, space):
        self.space = space
        self._pool = None
        self._switch_count = 0
        self._traced = {} # thread -> vars
        self.thread_count = 1
        self.blocked_count = 0

    def _init_head(self, thread):
        assert isinstance(thread, AppCoroutine), "type error"
        self._head = thread
        thread._next = thread._prev = thread
        assert self._head._next == self._head
        w("HEAD (main) THREAD = ", str(id(self._head)))
            
    def _chain_insert(self, thread):
        assert thread._next is thread, "thread._next not correctly linked"
        assert thread._prev is thread, "thread._prev not correctly linked"
        assert isinstance(thread, AppCoroutine), "type error"
        assert isinstance(thread._next, AppCoroutine), "type error"
        assert isinstance(thread._prev, AppCoroutine), "type error"
        r = self._head
        l = r._prev
        l._next = thread
        r._prev = thread
        thread._prev = l
        thread._next = r

    def hello(self):
        self._pool.hello_local_pool()

    def goodbye(self):
        self._pool.goodbye_local_pool()

    def register_var(self, var):
        space = self.space
        raise OperationError(space.w_AssertionError,
                             space.wrap('You cannot create a constraint variable '
                                        'in the top-level computation space.'))

    def is_blocked(self):
        return self.thread_count == self.blocked_count

    def is_failed(self):
        return False
    
    def is_stable(self):
        # second approx.
        return self.is_blocked() or self.is_failed()

    def is_runnable(self):
        if not self.is_stable():
            return True
        asking_from_within = [th for th in sched.uler._asking[self]
                              if th._cspace == self]
        return len(asking_from_within)

    def wait_stable(self):
        w("WAIT_STABLE on space", str(id(self)), "from space",
          str(id(get_current_cspace(self.space))))
        if self.is_stable():
            return
        curr = AppCoroutine.w_getcurrent(self.space)
        assert isinstance(curr, AppCoroutine), "type error"
        asking = sched.uler._asking
        if self in asking:
            asking[self][curr] = True
        else:
            asking[self] = {curr:True}
        sched.uler._blocked[curr] = True
        curr._cspace.blocked_count += 1
        sched.uler.schedule()

    def schedule(self):
        if not self.is_runnable():
            raise OperationError(self.space.w_AllBlockedError,
                                 self.space.wrap("ouch, that's a BUG"))
        to_be_run = self._select_next()
        if to_be_run == AppCoroutine.w_getcurrent(self.space):
            return
        assert isinstance(to_be_run, AppCoroutine), "type error"
        #w(".. SWITCHING (treads)", str(id(AppCoroutine.w_getcurrent(self.space))), "=>", str(id(to_be_run)))
        self._switch_count += 1
        to_be_run.w_switch() 
        
    def _select_next(self):
        to_be_run = self._head._next
        sentinel = to_be_run
        while to_be_run in sched.uler._blocked:
            if self.is_stable() and to_be_run in sched.uler._asking[self]:
                for th in sched.uler._asking[self]:
                    del sched.uler._blocked[th]
                    th._cspace.blocked_count -= 1
                sched.uler._asking[self] = {}
                break
            assert isinstance(to_be_run, AppCoroutine), "type error"
            to_be_run = to_be_run._next
            if to_be_run == sentinel:
                if not we_are_translated():
                    import pdb
                    pdb.set_trace()
        self._head = to_be_run
        return to_be_run

    def add_new_thread(self, thread):
        "insert 'thread' at end of running queue"
        w(".. ADDING thread", str(id(thread)), "to group", str(id(self)))
        assert isinstance(thread, AppCoroutine), "type error"
        self._chain_insert(thread)
        self.thread_count += 1

    def remove_thread(self, thread):
        assert isinstance(thread, AppCoroutine)
        w(".. REMOVING thread", str(id(thread)))
        assert thread not in sched.uler._blocked
        try:
            del self._traced[thread]
        except KeyError:
            w(".. removing non-traced thread")
        l = thread._prev
        r = thread._next
        l._next = r
        r._prev = l
        self._head = r
        if r == thread:
            # that means thread was the last one
            # the group is about to die
            pass
        thread._next = thread._prev = None
        self.thread_count -= 1
        if self.thread_count == 0:
            sched.uler.remove_group(self)

    # Logic Variables tracing, "accelerates" exception propagation
    # amongst threads
    def trace_vars(self, thread, lvars):
        assert isinstance(thread, AppCoroutine), "type error"
        assert isinstance(lvars, list), "type error"
        #w(".. TRACING logic vars.", str(lvars), "for", str(id(thread)))
        #assert not self._traced.has_key(thread) doesn't translate 
        self._traced[thread] = lvars

    def dirty_traced_vars(self, thread, failed_value):
        assert isinstance(thread, AppCoroutine)
        assert isinstance(failed_value, W_FailedValue)
        #w(".. DIRTYING traced vars")
        for w_var in self._traced[thread]:
            if self.space.is_true(self.space.is_free(w_var)):
                self.space.bind(w_var, failed_value)

    def w_threads(self):
        s = self.space
        thl = [s.newint(id(self._head))]
        assert isinstance(self._head, AppCoroutine)
        curr = self._head._next
        while curr != self._head:
            assert isinstance(curr, AppCoroutine)
            thl.append(s.newint(id(curr)))
            curr = curr._next
        w_t = W_ListObject(thl)
        return w_t

    def w_asking(self):
        asking = sched.uler._asking.get(self, None)
        if not asking:
            return self.space.w_None
        return W_ListObject([self.space.newint(id(th))
                             for th in asking.keys()]) 

    def group_info(self):
        s = self 
        si = self.space.setitem
        sw = self.space.wrap
        w_ret = self.space.newdict()
        si(w_ret, sw('switches'), self.space.newint(s._switch_count))
        si(w_ret, sw('threads'), s.w_threads())
        si(w_ret, sw('asking'), s.w_asking())
        return w_ret
        
#-- Misc --------------------------------------------------
def reset_scheduler(space):
    tg = W_ThreadGroupScheduler(space)
    tg._init_head(sched.main_thread)
    sched.uler = TopLevelScheduler(space, tg)
app_reset_scheduler = gateway.interp2app(reset_scheduler)

def sched_info(space):
    return sched.uler.sched_info()
app_sched_info = gateway.interp2app(sched_info)        

def schedule(space):
    "useful til we get preemtive scheduling deep into the vm"
    sched.uler.schedule()
app_schedule = gateway.interp2app(schedule)
