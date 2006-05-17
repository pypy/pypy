"""
The Stackless module allows you to do multitasking without using threads.
The essential objects are tasklets and channels.
Please refer to their documentation.
"""

from stackless import coroutine
from collections import deque

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

last_thread_id = 0

class TaskletProxy(object):
    def __init__(self, coro):
        self.alive = False
        self.atomic = False
        self.blocked = False
        self.frame = None
        self.ignore_nesting = False
        self.is_current = False
        self.is_main = False
        self.nesting_level = 0
        self.next = None
        self.paused = False
        self.prev = None
        self.recursion_depth = 0
        self.restorable = False
        self.scheduled = False
        self.thread_id = 0
        self.tempval = None
        self._coro = coro

    def __str__(self):
        return 'Tasklet-%s' % self.thread_id

    def __getattr__(self,attr):
        return getattr(self._coro,attr)

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

# channel: see below

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

# class tasklet: see below

# end interface

def _next():
    c = getcurrent()
    if c.next is c:
        return c
    nt = c.next
    if nt is main_tasklet and nt.next is not c:
        return nt.next
    else:
        return nt

def _insert(other):
    "put other on the end tasklet queue"
    this = getcurrent()
    #print '_insert:',this,
    #_print_queue()
    prev = this.prev
    this.prev = other
    other.next = this
    other.prev = prev
    prev.next = other
    other.blocked = False

def _priority_insert(other):
    "other will be the next tasklet"
    this = getcurrent()
    #print '_priority_insert:',this,
    #_print_queue()
    next = this.next
    this.next = other
    other.prev = this
    other.next = next
    next.prev = other
    other.blocked = False

def _remove(this):
    #print '_remove:',this,
    #_print_queue()
    if this.next is this:
        return
    t = c = getcurrent()
    count = 0
    while t is not this:
        if t is c and count:
            break
        count += 1
        t = t.next
    this.next.prev = this.prev
    this.prev.next = this.next

def _print_queue():
    c = s = getcurrent()
    print '[',c,
    while c.next is not s:
        c = c.next
        print c,
    print ']'

main_tasklet = None
main_coroutine = None

def __init():
    global main_tasklet
    global main_coroutine
    main_coroutine = c = coroutine.getcurrent()
    main_tasklet = TaskletProxy(c)
    main_tasklet.next = main_tasklet.prev = main_tasklet
    main_tasklet.is_main = True

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

    curr = coroutine.getcurrent()
    if curr is main_coroutine:
        return main_tasklet
    else:
        return curr

def getmain():
    return main_tasklet

def schedule(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    #print 'schedule: before switch',
    #_print_queue()
    curr = getcurrent()
    curr.is_current = False
    nt = _next()
    if curr.blocked:
        _remove(curr)
    nt.is_current = True
    nt.switch()
    #print 'schedule: after switch',
    #_print_queue()
    if retval is None:
        return getcurrent()
    else:
        return retval

"""
/***************************************************************************

    Tasklet Flag Definition
    -----------------------

    blocked:	    The tasklet is either waiting in a channel for
		    writing (1) or reading (-1) or not blocked (0).
		    Maintained by the channel logic. Do not change.

    atomic:	    If true, schedulers will never switch. Driven by
		    the code object or dynamically, see below.

    ignore_nesting: Allows auto-scheduling, even if nesting_level
		    is not zero.

    autoschedule:   The tasklet likes to be auto-scheduled. User driven.

    block_trap:     Debugging aid. Whenever the tasklet would be
		    blocked by a channel, an exception is raised.

    is_zombie:	    This tasklet is almost dead, its deallocation has
		    started. The tasklet *must* die at some time, or the
		    process can never end.

    pending_irq:    If set, an interrupt was issued during an atomic
		    operation, and should be handled when possible.


    Policy for atomic/autoschedule and switching:
    ---------------------------------------------
    A tasklet switch can always be done explicitly by calling schedule().
    Atomic and schedule are concerned with automatic features.

    atomic  autoschedule

	1	any	Neither a scheduler nor a watchdog will
			try to switch this tasklet.

	0	0	The tasklet can be stopped on desire, or it
			can be killed by an exception.

	0	1	Like above, plus auto-scheduling is enabled.

    Default settings:
    -----------------
    All flags are zero by default.

 ***************************************************************************/
"""

class tasklet(coroutine):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
    __slots__ = ['alive','atomic','blocked','frame',
                 'ignore_nesting','is_current','is_main',
                 'nesting_level','next','paused','prev','recursion_depth',
                 'restorable','scheduled','tempval','thread_id']

    ## note: most of the above should be properties

    ## note that next and prev are not here.
    ## should this be implemented, or better not?
    ## I think yes. it is easier to keep the linkage.
    ## tasklets gave grown this, and we can do different
    ## classes, later.
    ## well, it is a design question, but fow now probably simplest
    ## to just copy that.

    def __new__(cls, func=None):
        return super(tasklet,cls).__new__(cls)

    def __init__(self, func=None):
        global last_thread_id
        super(tasklet,self).__init__()
        self.alive = False
        self.atomic = False
        self.blocked = False
        self.frame = None
        self.ignore_nesting = False
        self.is_current = False
        self.is_main = False
        self.nesting_level = 0
        self.next = None
        self.paused = False
        self.prev = None
        self.recursion_depth = 0
        self.restorable = False
        self.scheduled = False
        last_thread_id += 1
        self.thread_id = last_thread_id
        self.tempval = None
        if func is not None:
            self.bind(func)

    def __call__(self, *argl, **argd):
        self.setup(*argl, **argd)
        return self

    def __str__(self):
        return 'Tasklet-%s' % self.thread_id

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
        self.tempval = func

    def insert(self):
        """
        Insert this tasklet at the end of the scheduler list,
        given that it isn't blocked.
        Blocked tasklets need to be reactivated by channels.
        """
        _insert(self)

    ## note: this is needed. please call coroutine.kill()
    def kill(self):
        """
        tasklet.kill -- raise a TaskletExit exception for the tasklet.
        Note that this is a regular exception that can be caught.
        The tasklet is immediately activated.
        If the exception passes the toplevel frame of the tasklet,
        the tasklet will silently die.
        """
        coroutine.kill(self)

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
        _remove(self)

    def run(self):
        """
        Run this tasklet, given that it isn't blocked.
        Blocked tasks need to be reactivated by channels.
        """
        _remove(self)
        _priority_insert(self)
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
        if self.tempval is None:
            raise TypeError('cframe function must be callable')
        coroutine.bind(self,self.tempval,*argl,**argd)
        self.tempval = None
        self.insert()

"""
/***************************************************************************

    Channel Flag Definition
    -----------------------


    closing:        When the closing flag is set, the channel does not
		    accept to be extended. The computed attribute
		    'closed' is true when closing is set and the
		    channel is empty.

    preference:	    0    no preference, caller will continue
		    1    sender will be inserted after receiver and run
		    -1   receiver will be inserted after sender and run

    schedule_all:   ignore preference and always schedule the next task

    Default settings:
    -----------------
    All flags are zero by default.

 ***************************************************************************/
"""

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
        self.queue = deque()
        self.closing = False
        self.preference = 0

    def __str__(self):
        return 'channel(' + str(self.balance) + ' : ' + str(self.queue) + ')'
    
    def _get_closed(self):
        return self.closing and not self.queue

    closed = property(_get_closed)

    ## note: needed
    def close(self):
        """
        channel.close() -- stops the channel from enlarging its queue.
        
        If the channel is not empty, the flag 'closing' becomes true.
        If the channel is empty, the flag 'closed' becomes true.
        """
        self.closing = True

    ## note: needed. iteration over a channel reads it all.
    def next(self):
        """
        x.next() -> the next value, or raise StopIteration
        """
        if self.closing and not self.balance:
            raise StopIteration()
        return self.receive()

    ## note: needed
    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """
        self.closing = False

    """
    /**********************************************************

      The central functions of the channel concept.
      A tasklet can either send or receive on a channel.
      A channel has a queue of waiting tasklets.
      They are either all waiting to send or all
      waiting to receive.
      Initially, a channel is in a neutral state.
      The queue is empty, there is no way to
      send or receive without becoming blocked.

      Sending 1):
        A tasklet wants to send and there is
        a queued receiving tasklet. The sender puts
        its data into the receiver, unblocks it,
        and inserts it at the top of the runnables.
        The receiver is scheduled.
      Sending 2):
        A tasklet wants to send and there is
        no queued receiving tasklet.
        The sender will become blocked and inserted
        into the queue. The next receiver will
        handle the rest through "Receiving 1)".
      Receiving 1):
        A tasklet wants to receive and there is
        a queued sending tasklet. The receiver takes
        its data from the sender, unblocks it,
        and inserts it at the end of the runnables.
        The receiver continues with no switch.
      Receiving 2):
        A tasklet wants to receive and there is
        no queued sending tasklet.
        The receiver will become blocked and inserted
        into the queue. The next sender will
        handle the rest through "Sending 1)".
     */
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
        if self.balance > 0: # Receiving 1
            wt = self.queue.popleft()
            retval = wt.tempval
            wt.tempval = None
            _insert(wt)
            self.balance -= 1
            return retval
        else: # Receiving 2
            ct = getcurrent()
            #_remove(ct)
            ct.blocked = True
            self.queue.append(ct)
            self.balance -= 1
            schedule()
            retval = ct.tempval
            ct.tempval = None
            return retval

    def send(self, msg):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        ct = getcurrent()
        if ct.tempval is not None:
            print 'THERE IS STILL SOME CHANNEL SEND VALUE',ct.tempval
        if self.balance < 0: # Sending 1
            wt = self.queue.popleft()
            wt.tempval = msg
            _priority_insert(wt)
            self.balance += 1
        else: # Sending 2
            ct.tempval = msg
            #_remove(ct)
            ct.blocked = True
            self.queue.append(ct)
            self.balance += 1
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

__init()

