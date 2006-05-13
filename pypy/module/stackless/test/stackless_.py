"""
The Stackless module allows you to do multitasking without using threads.
The essential objects are tasklets and channels.
Please refer to their documentation.
"""

from stackless import coroutine

__all__ = 'run getcurrent getmain schedule tasklet channel'.split()

# interface from original stackless
# class attributes are placeholders for some kind of descriptor
# (to be filled in later).

note = """
The bomb object decouples exception creation and exception
raising. This is necessary to support channels which don't
immediately react on messages.

This is a necessary Stackless 3.1 feature.
"""
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

note = """
cframes are an implementation detail.
Do not implement this now. If we need such a thing in PyPy,
then it will probably have a different layout.
"""
class cframe(object):
    """
    """
    __slots__ = ['f_back','obj1','obj2','obj3','i','n']

# channel: see below

note = """
The future of C stacks is undecided, yet. This applies
for Stackless, only at the moment. PyPy will use soft-switching
only, until we support external callbacks.
"""
class cstack(object):
    """
    A CStack object serves to save the stack slice which is involved
    during a recursive Python call. It will also be used for pickling
    of program state. This structure is highly platform dependant.
    Note: For inspection, str() can dump it as a string.
    """

note = """
I would implement it as a simple flag but let it issue
a warning that it has no effect.
"""
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
    """
    pass

note = """
Implementation can be deferred.
"""
def get_thread_info(thread_id):
    """
    get_thread_info(thread_id) -- return a 3-tuple of the thread's
    main tasklet, current tasklet and runcount.
    To obtain a list of all thread infos, use
    
    map (stackless.get_thread_info, stackless.threads)
    """
    pass

# def getcurrent() : see below

# def run(timeout): see below

# def schedule(retval=stackless.current) : see below

note = 'needed'
def schedule_remove(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    pass

note = """
should be implemented for debugging purposes. Low priority
"""
def set_channel_callback(callable):
    """
    set_channel_callback(callable) -- install a callback for channels.
    Every send/receive action will call the callback function.
    Example:
    def channel_cb(channel, tasklet, sending, willblock):
        ...
    sending and willblock are integers.
    Pass None to switch monitoring off again.
    """
    pass

note = """
should be implemented for debugging purposes. Low priority
"""
def set_schedule_callback(callable):
    """
    set_schedule_callback(callable) -- install a callback for scheduling.
    Every explicit or implicit schedule will call the callback function.
    Example:
    def schedule_cb(prev, next):
        ...
    When a tasklet is dying, next is None.
    When main starts up or after death, prev is None.
    Pass None to switch monitoring off again.
    """
    pass

note = """
this was an experiment on deriving from a module.
The idea was to make runcount and current into properties.
__tasklet__ and __channel__ are also not used.
It is ok to ignore these.
"""
class slpmodule(object):
    """
    The stackless module has a special type derived from
    the module type, in order to be able to override some attributes.
    __tasklet__ and __channel__ are the default types
    to be used when these objects must be instantiated internally.
    runcount, current and main are attribute-like short-hands
    for the getruncount, getcurrent and getmain module functions.
    """

# class tasklet: see below

note = 'drop'
def test_cframe(switches, words=0):
    """
    test_cframe(switches, words=0) -- a builtin testing function that does 
    nothing but tasklet switching. The function will call 
    PyStackless_Schedule() for switches times and then finish.
    If words is given, as many words will be allocated on the C stack.
    Usage: Create two tasklets for test_cframe and run them by run().
    
        t1 = tasklet(test_cframe)(500000)
        t2 = tasklet(test_cframe)(500000)
        run()
    This can be used to measure the execution time of 1.000.000 switches.
    """
    pass

note = 'drop'
def test_cframe_nr(switches):
    """
    test_cframe_nr(switches) -- a builtin testing function that does nothing
    but soft tasklet switching. The function will call 
    PyStackless_Schedule_nr() for switches times and then finish.
    Usage: Cf. test_cframe().
    """
    pass

note = 'drop'
def test_outside():
    """
    test_outside() -- a builtin testing function.
    This function simulates an application that does not run "inside"
    Stackless, with active, running frames, but always needs to initialize
    the main tasklet to get "\xednside".
    The function will terminate when no other tasklets are runnable.
    
    Typical usage: Create a tasklet for test_cframe and run by test_outside().
    
        t1 = tasklet(test_cframe)(1000000)
        test_outside()

    This can be used to measure the execution time of 1.000.000 switches.
    """
    pass


# end interface

main_tasklet = None
next_tasklet = None
scheduler = None

coro_reg = {}

def __init():
    global maintasklet
    mt = tasklet()
    mt._coro = c = coroutine.getcurrent()
    maintasklet = mt
    coro_reg[c] = mt

note = """
It is not needed to implement the watchdog feature right now.
But run should be supported in the way the docstring says.
The runner is always main, which must be removed while
running all the tasklets. The implementation below is wrong.
"""
def run():
    """
    run_watchdog(timeout) -- run tasklets until they are all
    done, or timeout instructions have passed. Tasklets must
    provide cooperative schedule() calls.
    If the timeout is met, the function returns.
    The calling tasklet is put aside while the tasklets are running.
    It is inserted back after the function stops, right before the
    tasklet that caused a timeout, if any.
    If an exception occours, it will be passed to the main tasklet.
    """
    schedule()

note = """
I don't see why coro_reg is needed.
tasklets should ideally inherit from coroutine.
This will create unwanted attributes, but they will
go away when we port this to interp-leve.
"""
def getcurrent():
    """
    getcurrent() -- return the currently executing tasklet.
    """

    c = coroutine.getcurrent()
    return coro_reg[c]

def getmain():
    return main_tasklet

def schedule():
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    scheduler.schedule()

class tasklet(object):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
#    __slots__ = ['alive','atomic','block_trap','blocked','frame',
#                 'ignore_nesting','is_current','is_main',
#                 'nesting_level','next','paused','prev','recursion_depth',
#                 'restorable','scheduled','thread_id']

    ## note: most of the above should be properties

    ## note that next and prev are not here.
    ## should this be implemented, or better not?
    ## I think yes. it is easier to keep the linkage.
    ## tasklets gave grown this, and we can do different
    ## classes, later.
    ## well, it is a design question, but fow now probably simplest
    ## to just copy that.

    def __init__(self, func=None):
        ## note: this field should reuse tempval to save space
        self._func = func

    def __call__(self, *argl, **argd):
        ## note: please inherit
        ## note: please use spaces after comma :-)
        ## note: please express this using bind and setup
        self._coro = c = coroutine()
        c.bind(self._func,*argl,**argd)
        coro_reg[c] = self
        self.insert()
        return self

    ## note: deprecated
    def become(self, retval=None):
        """
        t.become(retval) -- catch the current running frame in a tasklet.
        It is also inserted at the end of the runnables chain.
        If it is a toplevel frame (and therefore has no caller), an exception 
        is raised.  The function result is the tasklet itself. retval is 
        passed to the calling frame.
        If retval is not given, the tasklet is used as default.
        """
        pass

    ## note: __init__ should use this
    def bind(self):
        """
        Binding a tasklet to a callable object.
        The callable is usually passed in to the constructor.
        In some cases, it makes sense to be able to re-bind a tasklet,
        after it has been run, in order to keep its identity.
        Note that a tasklet can only be bound when it doesn't have a frame.
        """
        pass

    ## note: deprecated
    def capture(self, retval=None):
        """
        t.capture(retval) -- capture the current running frame in a tasklet,
        like t.become(). In addition the tasklet is run immediately, and the
        parent tasklet is removed from the runnables and returned as the value.
        """
        pass

    ## note: this is not part of the interface, please drop it
    cstate = None

    def insert(self):
        """
        Insert this tasklet at the end of the scheduler list,
        given that it isn't blocked.
        Blocked tasklets need to be reactivated by channels.
        """
        scheduler.insert(self)

    ## note: this is needed. please call coroutine.kill()
    def kill(self):
        """
        tasklet.kill -- raise a TaskletExit exception for the tasklet.
        Note that this is a regular exception that can be caught.
        The tasklet is immediately activated.
        If the exception passes the toplevel frame of the tasklet,
        the tasklet will silently die.
        """
        pass

    ## note: see the C implementation about how to use bombs
    def raise_exception(self, exc, value):
        """
        tasklet.raise_exception(exc, value) -- raise an exception for the 
        tasklet.  exc must be a subclass of Exception.
        The tasklet is immediately activated.
        """
        pass

    def remove(self):
        """
        Removing a tasklet from the runnables queue.
        Note: If this tasklet has a non-trivial C stack attached,
        it will be destructed when the containing thread state is destroyed.
        Since this will happen in some unpredictable order, it may cause 
        unwanted side-effects. Therefore it is recommended to either run 
        tasklets to the end or to explicitly kill() them.
        """
        scheduler.remove(self)

    def run(self):
        """
        Run this tasklet, given that it isn't blocked.
        Blocked tasks need to be reactivated by channels.
        """
        scheduler.setnexttask(self)
        ## note: please support different schedulers
        ## and don't mix calls to module functions with scheduler methods.
        schedule()

    ## note: needed at some point. right now just a property
    ## the stackless_flags should all be supported
    def set_atomic(self):
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
        pass

    ## note: see above
    def set_ignore_nesting(self,flag):
        """
        t.set_ignore_nesting(flag) -- set tasklet ignore_nesting status and 
        return current one. If set, the tasklet may be be auto-scheduled, 
        even if its nesting_level is > 0.
        This flag makes sense if you know that nested interpreter levels are 
        safe for auto-scheduling. This is on your own risk, handle with care!
        usage:
            tmp = t.set_ignore_nesting(1)
            # do critical stuff
            t.set_ignore_nesting(tmp)
        """
        pass

    ## note
    ## tasklet(func)(*args, **kwds)
    ## is identical to
    ## t = tasklet; t.bind(func); t.setup(*args, **kwds)
    def setup(self,*argl,**argd):
        """
        supply the parameters for the callable
        """
        pass

    ## note: this attribute should always be there.
    ## no class default needed.
    tempval = None

class channel(object):
    """
    A channel object is used for communication between tasklets.
    By sending on a channel, a tasklet that is waiting to receive
    is resumed. If there is no waiting receiver, the sender is suspended.
    By receiving from a channel, a tasklet that is waiting to send
    is resumed. If there is no waiting sender, the receiver is suspended.
    """

#    __slots__ = ['balance','closed','closing','preference','queue',
#                 'schedule_all']

    def __init__(self):
        self.balance = 0
        ## note: this is a deque candidate.
        self._readq = []
        self._writeq = []

    ## note: needed
    def close(self):
        """
        channel.close() -- stops the channel from enlarging its queue.
        
        If the channel is not empty, the flag 'closing' becomes true.
        If the channel is empty, the flag 'closed' becomes true.
        """
        pass

    ## note: needed. iteration over a channel reads it all.
    def next(self):
        """
        x.next() -> the next value, or raise StopIteration
        """
        pass

    ## note: needed
    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """

    def receive(self):
        """
        channel.receive() -- receive a value over the channel.
        If no other tasklet is already sending on the channel,
        the receiver will be blocked. Otherwise, the receiver will
        continue immediately, and the sender is put at the end of
        the runnables list.
        The above policy can be changed by setting channel flags.
        """
        ct = getcurrent()
        if self._writeq:
            (wt,retval), self._writeq = self._writeq[0], self._writeq[1:]
            scheduler.priorityinsert(wt)
            self.balance -= 1
            return retval
        else:
            self._readq.append(ct)
            scheduler.remove(ct)
            schedule()
            return self.receive()

    def send(self, msg):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        ct = getcurrent()
        scheduler.remove(ct)
        self._writeq.append((ct,msg))
        self.balance += 1
        if self._readq:
            nt, self._readq = self._readq[0], self._readq[1:]
            scheduler.priorityinsert(nt)
        schedule()

    ## note: see the C implementation on how to use bombs.
    def send_exception(self, exc, value):
        """
        channel.send_exception(exc, value) -- send an exception over the 
        channel. exc must be a subclass of Exception.
        Behavior is like channel.send, but that the receiver gets an exception.
        """
        pass

    ## needed
    def send_sequence(self, value):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        pass


class Scheduler(object):
    def __init__(self):
        ## note: better use a deque
        self.tasklist = []
        ## note: in terms of moving to interplevel, I would not do that
        self.nexttask = None 

    def empty(self):
        return not self.tasklist

    def __str__(self):
        return repr(self.tasklist) + '/%s' % self.nexttask

    def insert(self,task):
        if (task not in self.tasklist) and task is not maintasklet:
            self.tasklist.append(task)
        if self.nexttask is None:
            self.nexttask = 0

    def priorityinsert(self,task):
        if task in self.tasklist:
            self.tasklist.remove(task)
        if task is maintasklet:
            return
        if self.nexttask:
            self.tasklist.insert(self.nexttask,task)
        else:
            self.tasklist.insert(0,task)
            self.nexttask = 0

    def remove(self,task):
        try:
            i = self.tasklist.index(task)
            del(self.tasklist[i])
            if self.nexttask > i:
                self.nexttask -= 1
            if len(self.tasklist) == 0:
                self.nexttask = None
        except ValueError:pass

    def next(self):
        if self.nexttask is not None:
            task = self.tasklist[self.nexttask]
            self.nexttask += 1
            if self.nexttask == len(self.tasklist):
                self.nexttask = 0
            return task
        else:
            return maintasklet

    def setnexttask(self,task):
        if task not in self.tasklist:
            self.tasklist.insert(task)
        try:
            ## note: this is inefficient
            ## please use the flag attributes
            ## a tasklet 'knows' if it is in something
            i = self.tasklist.index(task)
            self.nexttask = i
        except IndexError:pass

    def schedule(self):
        n = self.next()
        n._coro.switch()

scheduler = Scheduler()
__init()

## note: nice work :-)

