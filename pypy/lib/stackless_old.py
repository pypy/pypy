"""
The Stackless module allows you to do multitasking without using threads.
The essential objects are tasklets and channels.
Please refer to their documentation.
"""

import traceback
import sys
try:
    deadtask = set()
except NameError:
    from sets import Set as set
    deadtask = set()


switches = 0

try:
    from _stackless import coroutine, greenlet
except ImportError: # we are running from CPython
    # you must have coroutine from
    # http://codespeak.net/svn/user/stephan/hacks/coroutine/
    # in your path in order to get the following to work

    from py.magic import greenlet
    from coroutine import coroutine

__all__ = 'run getcurrent getmain schedule tasklet \
                channel TaskletExit coroutine greenlet'.split()

main_tasklet = main_coroutine = None
scheduler = None
channel_hook = None
schedlock = False
_schedule_fasthook = None
_schedule_hook = None

class TaskletExit(Exception):pass

def SETNEXT(obj, val):
    "this function just makes debugging a bit easier :-)"
    obj.next = val

def SETPREV(obj, val):
    "just for debugging"
    obj.prev = val

def SETNONE(obj):
    "just for debugging"
    obj.prev = obj.next = None

def SWAPVAL(task1, task2):
    "just for debugging"
    assert task1 is not None
    assert task2 is not None
    task1.tempval, task2.tempval = task2.tempval, task1.tempval

def SETVAL(task, val):
    "just for debugging"
    assert task is not None
    task.tempval = val

last_task_id = 0

def restore_exception(etype, value, stack):
    """until I find out how to restore an exception on python level"""
    #sys.excepthook(etype, value, stack)
    raise etype, value, stack
    #raise etype(value)

class TaskletProxy(object):
    """TaskletProxy is needed to give the main_coroutine tasklet behaviour"""
    def __init__(self, coro):
        self.alive = True
        self.atomic = False
        self.blocked = 0
        self.block_trap = False
        self.frame = None
        self.ignore_nesting = False
        self.is_current = False
        self.is_main = False
        self.nesting_level = 0
        self.next = self.prev = None
        self.paused = False
        self.recursion_depth = 0
        self.restorable = False
        self.scheduled = False
        self.task_id = 0
        self.tempval = None
        self._coro = coro

    def __repr__(self):
        return tasklet.__str__(self)

    __str__ = __repr__

    def __getattr__(self,attr):
        return getattr(self._coro,attr)

    def __reduce__(self):
        return getmain, ()

class bomb(object):
    """
    A bomb object is used to hold exceptions in tasklets.
    Whenever a tasklet is activated and its tempval is a bomb,
    it will explode as an exception.
    
    You can create a bomb by hand and attach it to a tasklet if you like.
    Note that bombs are 'sloppy' about the argument list, which means that
    the following works, although you should use '*sys.exc_info()'.
    
    from stackless import *; import sys
    t = tasklet(lambda:42)()
    try: 1/0
    except: b = bomb(sys.exc_info())
    
    t.tempval = b
    nt.run()  # let the bomb explode
    """

    traceback = None
    type = None
    value = None

    def __init__(self,etype=None, value=None, traceback=None):
        self.type = etype
        self.value = value
        self.traceback = traceback

    def _explode(self):
        restore_exception(self.type, self.value, self.traceback)

def make_deadlock_bomb():
    return bomb(RuntimeError, 
        RuntimeError("Deadlock: the last runnable tasklet cannot be blocked."),
        None)

def curexc_to_bomb():
    return bomb(*sys.exc_info())

def enable_softswitch(flag):
    """
    enable_softswitch(flag) -- control the switching behavior.
    Tasklets can be either switched by moving C stack slices around
    or by avoiding stack changes at all. The latter is only possible
    in the top interpreter level. Switching it off is for timing and
    debugging purposes. This flag exists once for the whole process.
    For inquiry only, use the phrase
    ret = enable_softswitch(0); enable_softswitch(ret)
    By default, soft switching is enabled.

    This is not implemented yet!!!!
    """
    pass

def get_thread_info(task_id):
    """
    get_thread_info(task_id) -- return a 3-tuple of the thread's
    main tasklet, current tasklet and runcount.
    To obtain a list of all thread infos, use
    
    map (stackless.get_thread_info, stackless.threads)

    This is not implemented yet!!!!
    """
    pass

def set_channel_callback(callable):
    """
    set_channel_callback(callable) -- install a callback for channels.
    Every send/receive action will call the callback function.
    Example:
    def channel_cb(channel, tasklet, sending, willblock):
        ...
    sending and willblock are booleans.
    Pass None to switch monitoring off again.
    """
    global channel_hook

    channel_hook = callable

def _schedule_callback(prev, next):
    global _schedule_hook
    return _schedule_hook(prev, next)

def set_schedule_callback(func):
    """
    set_schedule_callback(callable) -- install a callback for scheduling.
    Every explicit or implicit schedule will call the callback function
    right before the switch is actually done.
    Example:
    def schedule_cb(prev, next):
        ...
    When a tasklet is dying, next is None.
    When main starts up or after death, prev is None.
    Pass None to switch monitoring off again.
    """
    global _schedule_fasthook
    global _schedule_hook
    global _schedule_callback

    if func is not None and not callable(func):
        raise TypeError("schedule callback nust be callable")
    _schedule_hook = func
    if func is None:
        _schedule_fasthook = None
    else:
        _schedule_fasthook = _schedule_callback

def run(timeout=0):
    """
    run_watchdog(timeout) -- run tasklets until they are all
    done, or timeout instructions have passed. Tasklets must
    provide cooperative schedule() calls.
    If the timeout is met, the function returns.
    The calling tasklet is put aside while the tasklets are running.
    It is inserted back after the function stops, right before the
    tasklet that caused a timeout, if any.
    If an exception occours, it will be passed to the main tasklet.

    Please note that the 'timeout' feature is not yet implemented
    """
    me = scheduler.current_remove()
    if me is not main_tasklet:
        raise RuntimeError("run() must be run from the main thread's \
                             main tasklet")
    return scheduler.schedule_task(me, scheduler._head)

def getcurrent():
    """
    getcurrent() -- return the currently executing tasklet.
    """

    curr = coroutine.getcurrent()
    if curr is main_coroutine:
        return main_tasklet
    else:
        return curr

def getmain():
    return main_tasklet

def _do_schedule(retval=None, remove=False):
    prev = scheduler._head
    next = prev.next
    if remove:
        scheduler.current_remove()
    ret = scheduler.schedule_task(prev, next)
    if retval is None:
        return ret
    else:
        return retval

def schedule_remove(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    return _do_schedule(retval, True)

def schedule(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    return _do_schedule(retval, False)

class tasklet(coroutine):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
    __slots__ = ['alive','atomic','blocked','block_trap','frame',
                 'ignore_nesting','is_current','is_main',
                 'nesting_level','next','paused','prev','recursion_depth',
                 'restorable','scheduled','tempval','task_id']

    def __new__(cls, func=None):
        return super(tasklet,cls).__new__(cls)

    def __init__(self, func=None):
        global last_task_id
        super(tasklet,self).__init__()
        self.alive = False
        self.atomic = False
        self.blocked = 0
        self.block_trap = False
        self.frame = None
        self.ignore_nesting = False
        self.is_current = False
        self.is_main = False
        self.nesting_level = 0
        self.next = self.prev = None
        self.paused = False
        self.recursion_depth = 0
        self.restorable = False
        self.scheduled = False
        last_task_id += 1
        self.task_id = last_task_id
        self.tempval = None
        if func is not None:
            self.bind(func)

    def __call__(self, *argl, **argd):
        self.setup(*argl, **argd)
        return self

    def __repr__(self):
        next = None
        if self.next is not None:
            next = self.next.task_id
        prev = None
        if self.prev is not None:
            prev = self.prev.task_id
        if self.blocked:
            bs = 'b'
        else:
            bs = '-'
        return 'T%s(%s) (%s, %s)' % (self.task_id, bs, next, prev)

    __str__ = __repr__

    def bind(self, func):
        """
        Binding a tasklet to a callable object.
        The callable is usually passed in to the constructor.
        In some cases, it makes sense to be able to re-bind a tasklet,
        after it has been run, in order to keep its identity.
        Note that a tasklet can only be bound when it doesn't have a frame.
        """
        if not callable(func):
            raise TypeError('tasklet function must be a callable')
        SETVAL(self, func)

    def insert(self):
        """
        Insert this tasklet at the end of the scheduler list,
        given that it isn't blocked.
        Blocked tasklets need to be reactivated by channels.
        """
        if self.blocked:
            raise RuntimeError('You cannot run a blocked tasklet')
        if self.is_zombie:
            raise RuntimeError('You cannot run an unbound(dead) tasklet')
        if self.next is None:
            scheduler.current_insert(self)

    def kill(self):
        """
        tasklet.kill -- raise a TaskletExit exception for the tasklet.
        Note that this is a regular exception that can be caught.
        The tasklet is immediately activated.
        If the exception passes the toplevel frame of the tasklet,
        the tasklet will silently die.
        """
        if not self.is_zombie:
            coroutine.kill(self)
        return self.raise_exception(TaskletExit, TaskletExit())

    def raise_exception(self, exc, value):
        """
        tasklet.raise_exception(exc, value) -- raise an exception for the 
        tasklet.  exc must be a subclass of Exception.
        The tasklet is immediately activated.
        """
        b = bomb(exc, value)
        SETVAL(self, b)
        return scheduler.schedule_task(getcurrent(), self)

    def remove(self):
        """
        Removing a tasklet from the runnables queue.
        Note: If this tasklet has a non-trivial C stack attached,
        it will be destructed when the containing thread state is destroyed.
        Since this will happen in some unpredictable order, it may cause 
        unwanted side-effects. Therefore it is recommended to either run 
        tasklets to the end or to explicitly kill() them.
        """
        scheduler.current_remove(self)

    def run(self):
        """
        Run this tasklet, given that it isn't blocked.
        Blocked tasks need to be reactivated by channels.
        """
        scheduler.schedule_task(getcurrent(), self)

    def set_atomic(self, val):
        """
        t.set_atomic(flag) -- set tasklet atomic status and return current one.
        If set, the tasklet will not be auto-scheduled.
        This flag is useful for critical sections which should not be 
        interrupted.
        usage:
            tmp = t.set_atomic(1)
            # do critical stuff
            t.set_atomic(tmp)
        Note: Whenever a new tasklet is created, the atomic flag is initialized
        with the atomic flag of the current tasklet.Atomic behavior is 
        additionally influenced by the interpreter nesting level.
        See set_ignore_nesting.
        """
        tmpval = self.atomic
        self.atomic = val
        return tmpval

    def set_ignore_nesting(self, flag):
        """
        t.set_ignore_nesting(flag) -- set tasklet ignore_nesting status and 
        return current one. If set, the tasklet may be auto-scheduled, 
        even if its nesting_level is > 0.
        This flag makes sense if you know that nested interpreter levels are 
        safe for auto-scheduling. This is on your own risk, handle with care!
        usage:
            tmp = t.set_ignore_nesting(1)
            # do critical stuff
            t.set_ignore_nesting(tmp)

        Please note that this piece of code does effectively nothing.
        """
        tmpval = self.ignore_nesting
        self.ignore_nesting = flag
        return tmpval

    def finished(self, excinfo):
        """called, when coroutine is finished. This gives the tasklet
           a chance to clean up after himself."""

        if self.alive:
            self.alive = False
            if self.next is not self:
                next = self.next
            else:
                next = getmain()
            scheduler.remove_task(self)
            deadtask.add(self)
            prev = self
            if excinfo[0] is not None:
                et = excinfo[0]
                ev = excinfo[1]
                tr = excinfo[2]
                b = bomb(et, et(ev), tr)
                next = getmain()
                SETVAL(next, b)
            scheduler.schedule_task(prev, next)

    def setup(self, *argl, **argd):
        """
        supply the parameters for the callable
        """
        if self.tempval is None:
            raise TypeError('cframe function must be callable')
        coroutine.bind(self,self.tempval,*argl,**argd)
        SETVAL(self, None)
        self.alive = True
        self.insert()

    def __reduce__(self):
        # xxx save more
        one, two, three = coroutine.__reduce__(self)
        assert one is coroutine
        assert two == ()
        return tasklet, (), (three, self.alive, self.tempval)

    def __setstate__(self, (coro_state, alive, tempval)):
        coroutine.__setstate__(self, coro_state)
        self.alive = alive
        self.tempval = tempval

def channel_callback(chan, task, sending, willblock):
    return channel_hook(chan, task, sending, willblock)

class channel(object):
    """
    A channel object is used for communication between tasklets.
    By sending on a channel, a tasklet that is waiting to receive
    is resumed. If there is no waiting receiver, the sender is suspended.
    By receiving from a channel, a tasklet that is waiting to send
    is resumed. If there is no waiting sender, the receiver is suspended.
    """

    def __init__(self):
        self.balance = 0
        self.closing = False
        self.preference = -1
        self.next = self.prev = self
        self.schedule_all = False
        self.task_id = -2

    def __str__(self):
        parts = ['%s' % x.task_id for x in self._content()]
        return 'channel(' + str(self.balance) + '): ['+' -> '.join(parts)+']'
    
    def _get_closed(self):
        return self.closing and self.next is None

    closed = property(_get_closed)

    def _channel_insert(self, task, d):
        self._ins(task)
        self.balance += d
        task.blocked = d

    def _content(self):
        visited = set((self,))
        items = []
        next = self.next
        if next is not self:
            while next is not None and next not in visited:
                items.append(next)
                visited.add(next)
                next = next.next
        return items

    def _queue(self):
        if self.next is self:
            return None
        else:
            return self.next

    def _channel_remove(self, d):
        ret = self.next
        assert isinstance(ret, (tasklet, TaskletProxy))
        self.balance -= d
        self._rem(ret)
        ret.blocked = 0

        return ret

    def channel_remove_specific(self, d, task):
        # note: we assume that the task is in the channel
        self.balance -= d
        self._rem(task)
        task.blocked = 0

        return task

    def _ins(self, task):
        if (task.next is not None) or (task.prev is not None):
            raise AssertionError('task.next and task.prev must be None')
        # insert at end
        SETPREV(task, self.prev)
        SETNEXT(task, self)
        SETNEXT(self.prev, task)
        SETPREV(self, task)

    def _rem(self, task):
        assert task.next is not None
        assert task.prev is not None
        #remove at end
        SETPREV(task.next, task.prev)
        SETNEXT(task.prev, task.next)
        SETNONE(task)

    def _notify(self, task, d, cando, res):
        global schedlock
        global channel_hook
        if channel_hook is not None:
            if schedlock:
                raise RuntimeError('Recursive channel call due to callbacks!')
            schedlock = 1
            channel_callback(self, task, d > 0, not cando)
            schedlock = 0

    def _channel_action(self, arg, d, stackl):
        source = scheduler._head
        target = self.next
        assert source is getcurrent()
        interthread = 0 # no interthreading at the moment
        if d > 0:
            cando = self.balance < 0
        else:
            cando = self.balance > 0

        assert abs(d) == 1
        SETVAL(source, arg)
        if not interthread:
            self._notify(source, d, cando, None)
        if cando:
            # communication 1): there is somebody waiting
            target = self._channel_remove(-d)
            SWAPVAL(source, target)
            if interthread:
                raise Exception('no interthreading: I can not be reached...')
            else:
                if self.schedule_all:
                    scheduler.current_insert(target)
                    target = source.next
                elif self.preference == -d:
                    scheduler._set_head(source.next)
                    scheduler.current_insert(target)
                    scheduler._set_head(source)
                else:
                    scheduler.current_insert(target)
                    target = source
        else:
            # communication 2): there is nobody waiting
            if source.block_trap:
                raise RuntimeError("this tasklet does not like to be blocked")
            if self.closing:
                raise StopIteration()
            scheduler.current_remove()
            self._channel_insert(source, d)
            target = scheduler._head
        retval = scheduler.schedule_task(source, target)
        if interthread:
            self._notify(source, d, cando, None)
        return retval

    def close(self):
        """
        channel.close() -- stops the channel from enlarging its queue.
        
        If the channel is not empty, the flag 'closing' becomes true.
        If the channel is empty, the flag 'closed' becomes true.
        """
        self.closing = True

    def next(self):
        """
        x.next() -> the next value, or raise StopIteration
        """
        if self.closing and not self.balance:
            raise StopIteration()
        yield self.receive()

    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """
        self.closing = False

    def receive(self):
        """
        channel.receive() -- receive a value over the channel.
        If no other tasklet is already sending on the channel,
        the receiver will be blocked. Otherwise, the receiver will
        continue immediately, and the sender is put at the end of
        the runnables list.
        The above policy can be changed by setting channel flags.
        """
        return self._channel_action(None, -1, 1)

    def send(self, msg):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        return self._channel_action(msg, 1, 1)

    def send_exception(self, exc, value):
        """
        channel.send_exception(exc, value) -- send an exception over the 
        channel. exc must be a subclass of Exception.
        Behavior is like channel.send, but that the receiver gets an exception.
        """
        b = bomb(exc, value)
        self.send(bomb)

    def send_sequence(self, value):
        """
        channel.send_sequence(seq) -- sed a stream of values
        over the channel. Combined with a generator, this is
        a very efficient way to build fast pipes.
        """
        for item in value:
            self.send(item)

class Scheduler(object):
    """The singleton Scheduler. Provides mostly scheduling convenience
       functions. In normal circumstances, scheduler._head point the
       current running tasklet. _head and current_tasklet might be
       out of sync just before the actual task switch takes place."""

    def __init__(self):
        self._set_head(getcurrent())

    def _cleanup(self, task):
        task.alive = False
        self.remove_task(task)
        if self._head is None:
            self.current_insert(main_tasklet)
        self.schedule_task(getcurrent(), self._head)

    def _set_head(self, task):
        self._head = task

    def reset(self):
        self.__init__()

    def __len__(self):
        return len(self._content())

    def _content(self):
        "convenience method to get the tasklets that are in the queue"
        visited = set()
        items = []
        next = self._head
        if next is not self:
            while next is not None and next not in visited:
                items.append(next)
                visited.add(next)
                next = next.next
        return items

    def __str__(self):
        parts = ['%s' % x.task_id for x in self._content()]
        if self._head is not self:
            currid = self._head.task_id
        else:
            currid = -1
        return 'Scheduler: [' + ' -> '.join(parts) + ']'

    def _chain_insert(self, task):
        assert task.next is None
        assert task.prev is None
        if self._head is None:
            SETNEXT(task, task)
            SETPREV(task, task)
            self._set_head(task)
        else:
            r = self._head
            l = r.prev
            SETNEXT(l, task)
            SETPREV(r, task)
            SETPREV(task, l)
            SETNEXT(task, r)

    def remove_task(self, task):
        l = task.prev
        r = task.next
        SETNEXT(l, r)
        SETPREV(r, l)
        self._set_head(r)
        if r == task:
            self._set_head(None)
        SETNONE(task)

        return task

    def _chain_remove(self):
        if self._head is None: 
            return None
        return self.remove_task(self._head)

    def current_insert(self, task):
        "insert 'task' at end of running queue"
        self._chain_insert(task)

    def current_insert_after(self, task):
        "insert 'task' just after the current one"
        if self._head is not None:
            curr = self._head
            self._set_head(curr.next)
            self._chain_insert(task)
            self._set_head(curr)
        else:
            self.current_insert(task)

    def current_remove(self):
        "remove current tasklet from queue"
        return self._chain_remove()

    def channel_remove_slow(self, task):
        prev = task.prev
        while not isinstance(prev, channel):
            prev = prev.prev
        chan = prev
        assert chan.balance
        if chan.balance > 0:
            d = 1
        else:
            d = -1
        return chan.channel_remove_specific(d, task)

    def bomb_explode(self, task):
        thisbomb = task.tempval
        assert isinstance(thisbomb, bomb)
        SETVAL(task, None)
        thisbomb._explode()
#        try:
#            thisbomb._explode()
#        finally:
#            if getcurrent() == main_tasklet:
#                sys.excepthook(thisbomb.type, 
#                               thisbomb.value, 
#                               thisbomb.traceback)
#                sys.exit()
        
    def _notify_schedule(self, prev, next, errflag):
        if _schedule_fasthook is not None:
            global schedlock
            if schedlock:
                raise RuntimeError('Recursive scheduler call due to callbacks!')
            schedlock = True
            ret = _schedule_fasthook(prev, next)
            schedlock = False
            if ret:
                return errflag

    def schedule_task_block(self, prev):
        if main_tasklet.next is None:
            if isinstance(prev.tempval, bomb):
                SETVAL(main_tasklet, prev.tempval)
            return self.schedule_task(prev, main_tasklet)
        retval = make_deadlock_bomb()
        SETVAL(prev, retval)

        return self.schedule_task(prev, prev)

    def schedule_task(self, prev, next):
        global switches
        switches += 1
        myswitch = switches
        if next is None:
            return self.schedule_task_block(prev)
        if next.blocked:
            self.channel_remove_slow(next)
            self.current_insert(next)
        elif next.next is None:
            self.current_insert(next)
        if prev is next:
            retval = prev.tempval
            if isinstance(retval, bomb):
                self.bomb_explode(prev)
            return retval
        self._notify_schedule(prev, next, None)
        self._set_head(next)

        try:
            res = next.switch()
        except:
            pass

        for dead in tuple(deadtask):
            deadtask.discard(dead)

            # the code below should work, but doesn't

            #if not dead.is_zombie:
            #    coroutine.kill(dead)
            #    del dead

        retval = prev.tempval
        if isinstance(retval, bomb):
            self.bomb_explode(prev)

        return retval

    def schedule_callback(self, prev, next):
        ret = _schedule_hook(prev, next)
        if ret:
            return 0
        else:
            return -1

    def __reduce__(self):
        if self is scheduler:
            return _return_sched, (), ()

def _return_sched():
    return scheduler

def __init():
    global main_tasklet
    global main_coroutine
    global scheduler 
    main_coroutine = c = coroutine.getcurrent()
    main_tasklet = TaskletProxy(c)
    SETNEXT(main_tasklet, main_tasklet)
    SETPREV(main_tasklet, main_tasklet)
    main_tasklet.is_main = True
    scheduler = Scheduler()

__init()

_init = __init # compatibility to stackless_new

